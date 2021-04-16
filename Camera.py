import cv2
import PySpin
import numpy as np
import ffmpeg
from utils.calibration_utils import Calib
import pandas as pd
from dlclive import DLCLive, Processor
from AcquisitionObject import AcquisitionObject
from utils.image_draw_utils import draw_dots
import os


FRAME_TIMEOUT = 100  # time in milliseconds to wait for pyspin to retrieve the frame
DLC_RESIZE = 0.6  # resize the frame by this factor for DLC
DLC_UPDATE_EACH = 3  # frame interval for DLC update
TOP_CAM = '17391304'
TEMP_PATH = r'C:\Users\SchwartzLab\PycharmProjects\bahavior_rig\config'


class Camera(AcquisitionObject):

  def __init__(self, parent, camlist, index, frame_rate, address):

    self._spincam = camlist.GetByIndex(index)
    self._spincam.Init()

    # hardware triggering
    self._spincam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
    # self._spincam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame)
    # trigger has to be off to change source
    self._spincam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
    self._spincam.TriggerSource.SetValue(PySpin.TriggerSource_Line0)
    self._spincam.TriggerMode.SetValue(PySpin.TriggerMode_On)

    self.device_serial_number, self.height, self.width = self.get_camera_properties()

    AcquisitionObject.__init__(
        self, parent, frame_rate, (self.width, self.height), address)
    self.is_top = True if self.device_serial_number == TOP_CAM else False

  # TODO: make sure this step should be in prepare_display or prepare_run

  def prepare_run(self):  # TODO: prepare_run?
    self._spincam.BeginAcquisition()

  def end_run(self):
    self._spincam.EndAcquisition()

  def prepare_processing(self, options):
    process = {}

    if options['mode'] == 'DLC':
      # process['modelpath'] = options
      process['mode'] = 'DLC'
      process['processor'] = Processor()
      process['DLCLive'] = DLCLive(
          model_path=options['modelpath'],
          processor=process['processor'],
          display=False,
          resize=DLC_RESIZE)
      process['frame0'] = True
      return process
    else:  # mode should be 'intrinsic' or 'extrinsic'
      process['mode'] = options['mode']

      # could move this to init if desired
      process['calibrator'] = Calib(options['mode'])
      process['calibrator'].load_in_config(self.device_serial_number)
      # TODO: is there a better to handle recording during calibration?
      if process['mode'] == 'extrinsic':
        path = os.path.join(
            TEMP_PATH, 'config_extrinsic_%s_temp.MOV' % self.device_serial_number)
        # temporarily save recorded video to path
        self.file = path

      return process
      # process['calibrator'].root_config_path= self.file # does this return the file path?

      # process['calibrator'].reset()
      # if options['mode'] == 'extrinsic':
      # process['calibrator'].load_ex_config(self.device_serial_number)

  def end_processing(self, process):
    if process['mode'] == 'DLC':
      process['DLCLive'].close()
      process['frame0'] = False
      status = 'DLC Live turned off'
    else:
      status = process['calibrator'].save_temp_config(
          self.device_serial_number, self.width, self.height)
      self.print(status)
      del process['calibrator']  # could move this to close if desired
    # TODO:status should be put on the screen!
    return status

  def do_process(self, data, data_count, process):
    if process['mode'] == 'DLC':
      if process['frame0']:
        process['DLCLive'].init_inference(frame=data)
        process['frame0'] = False
        pose = process['DLCLive'].get_pose(data)
        return pose, process
      else:
        return process['DLCLive'].get_pose(data), None
    elif process['mode'] == 'intrinsic':
      result = process['calibrator'].in_calibrate(
          data, data_count, self.device_serial_number)
      return result, None

    elif process['mode'] == 'alignment':
      result = process['calibrator'].al_calibrate(data, data_count)
      return result, None

    elif process['mode'] == 'extrinsic':
      result = process['calibrator'].ex_calibrate(data, data_count)
      return result, None

  def capture(self, data):
    while True:
      # get the image from spinview
      try:
        im = self._spincam.GetNextImage(FRAME_TIMEOUT)

      except PySpin.SpinnakerException as e:
        self.print(f'Error in spinnaker: {e}. Assumed innocuous.')
        continue

      # for single frame mode:
      # self._spincam.EndAcquisition()
      # self._spincam.BeginAcquisition()

      if im.IsIncomplete():
        status = im.GetImageStatus()
        im.Release()
        raise Exception(f"Image incomplete with image status {status} ...")
      data = im.GetNDArray()
      im.Release()
      yield data

  def open_file(self, filepath):
    # path = os.path.join(filepath, f'{self.device_serial_number}.mp4')
    self.print(f'saving camera data to {filepath}')
    return ffmpeg \
        .input('pipe:', format='rawvideo', pix_fmt='gray', s=f'{self.width}x{self.height}', framerate=self.run_rate) \
        .output(filepath, vcodec='libx265') \
        .overwrite_output() \
        .global_args('-loglevel', 'error') \
        .run_async(pipe_stdin=True, quiet=True)
    # .run_async(pip_stdin=True)

  def close_file(self, fileObj):
    fileObj.stdin.close()
    fileObj.wait()
    del fileObj

  def save(self, data):
    self._file.stdin.write(data.tobytes())

  def get_camera_properties(self):
    nodemap_tldevice = self._spincam.GetTLDeviceNodeMap()
    device_serial_number = PySpin.CStringPtr(
        nodemap_tldevice.GetNode('DeviceSerialNumber')).GetValue()
    nodemap = self._spincam.GetNodeMap()
    height = PySpin.CIntegerPtr(nodemap.GetNode('Height')).GetValue()
    width = PySpin.CIntegerPtr(nodemap.GetNode('Width')).GetValue()
    return device_serial_number, height, width

  def predisplay(self, frame):
    # TODO: still get frame as input? but should return some kind of dictionary? or array?
    # TODO: where does this get called from?
    # TODO: make sure text is not overlapping
    process = self.processing
    #######
    # data_count = self.data_count
    # cv2.putText(frame,str(data_count),(50, 50),cv2.FONT_HERSHEY_PLAIN,3.0,255,2)
    # print(f'sent frame {data_count}')
    #######
    if process is not None:
      results = self.results
      if results is not None:
        if process['mode'] == 'DLC':
          draw_dots(frame, results)
        else:
          cv2.putText(frame, f"Performing {process['mode']} calibration", (50, 50),
                      cv2.FONT_HERSHEY_PLAIN, 4.0, (255, 0, 125), 2)

          if str(self.device_serial_number) != str(TOP_CAM) and process['mode'] == 'intrinsic':
            if 'calibrator' in process.keys():
              cv2.drawChessboardCorners(
                  frame, (process['calibrator'].x, process['calibrator'].y), results['corners'], results['ret'])
          else:
            if len(results['corners']) != 0:
              cv2.aruco.drawDetectedMarkers(
                  frame, results['corners'], results['ids'], borderColor=225)

          if process['mode'] == 'alignment':
            if results['allDetected']:
              text = 'Enough corners detected! Ready to go'
            else:
              text = "Not enough corners! Please adjust the camera"

            cv2.putText(frame, text, (500, 1000),
                        cv2.FONT_HERSHEY_PLAIN, 2.0, (255, 0, 255), 2)
          if process['mode'] == 'extrinsic':
            if results['ids'] is None:
              text = 'Missing board or intrinsic calibration file'
              cv2.putText(frame, text, (500, 1000),
                          cv2.FONT_HERSHEY_PLAIN, 2.0, (255, 0, 255), 2)
    return frame #gets drawn to screen

#  def end_run(self):
#    if self.file:
#      copy_config(self.file)

  def close(self):
    self._spincam.DeInit()

  def __del__(self):
    self._spincam.DeInit()
