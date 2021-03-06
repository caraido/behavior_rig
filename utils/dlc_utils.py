import deeplabcut
import os
import threading

DLC_LIVE_MODEL_PATH=r'C:\Users\SchwartzLab\PycharmProjects\bahavior_rig\DLC\Alec_second_try-Devon-2020-12-07\exported-models\DLC_Alec_second_try_resnet_50_iteration-0_shuffle-1'
TOP_THRESHOLD=0.85
SIDE_THRESHOLD=0.5


def is_fully_analyzed(path):
	items=os.listdir(path)
	h5=[i for i in items if '.h5' in i]
	if len(h5)==4:
		return True
	else:
		return False


def dlc_analysis(root_path, dlc_config_path):
	if isinstance(dlc_config_path, list) and not is_fully_analyzed(root_path):
		top_config = dlc_config_path[0]
		side_config = dlc_config_path[1]
		things = os.listdir(root_path)

		top = [a for a in things if '.MOV' in a and '17391304' in a]
		# top_path = [os.path.join(processed_path, top[i]) for i in range(len(top))]
		top_path = [os.path.join(root_path, top[i]) for i in range(len(top))]
		side = [a for a in things if '.MOV' in a and '17391304' not in a]
		# side_path = [os.path.join(processed_path, side[i]) for i in range(len(side))]
		side_path = [os.path.join(root_path, side[i]) for i in range(len(side))]

		# top camera
		deeplabcut.analyze_videos(top_config,
								  top_path,
								  save_as_csv=True,
								  videotype='mov',
								  shuffle=1,
								  gputouse=0)

		arguments={'config':top_config,
					'videos':top_path,
					'save_frames':False,
					'trailpoints':1,
					'videotype':'mov',
					"draw_skeleton":'True'}
		create_labeled_video_top_thread=threading.Thread(target=deeplabcut.create_labeled_video,kwargs=arguments)
		create_labeled_video_top_thread.start()

		#deeplabcut.create_labeled_video(top_config,
		#								top_path,
		#								save_frames=False,
		#								trailpoints=1,
		#								videotype='mov',
		#								draw_skeleton='True')
		# side cameras
		deeplabcut.analyze_videos(side_config,
								  side_path,
								  save_as_csv=True,
								  videotype='mov',
								  shuffle=1,
								  gputouse=0)

		arguments={'config':side_config,
					'videos':side_path,
					'save_frames':False,
					'trailpoints':1,
					'videotype':'mov',
					"draw_skeleton":'True'}
		create_labeled_video_side_thread = threading.Thread(target=deeplabcut.create_labeled_video, kwargs=arguments)
		create_labeled_video_side_thread.start()

		return create_labeled_video_top_thread,create_labeled_video_side_thread
	else:
		return None


