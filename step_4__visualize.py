'''
Make a movie visualizing the scenting classification &
orientation estimation data on frames to label scenting bees
and their scenting directions.
'''

###### IMPORTS ######
import os
import sys
import cv2
import glob
import glob2
import json
import argparse
import pandas as pd
import numpy as np
import csv
import subprocess
import utils.image as image_utils
from tqdm import tqdm
import math

# Plotting
import seaborn as sns
import matplotlib.pyplot as plt
sns.set(style="ticks")
plt.rcParams["font.family"] = "Arial"

import utils.general as general_utils
from utils.settings import COLORS

###### HELPER FUNCTIONS ######
def get_wanted_frames(start_frame, end_frame, all_frames):
    start_num = int(start_frame.split('_')[1])
    end_num = int(end_frame.split('_')[1])
    wanted_frames = np.arange(start_num, end_num+1)
    all_frame_nums = np.array([int(os.path.basename(frame).split('_')[1].split('.')[0])
                               for frame in all_frames])
    condition_1 = np.in1d(all_frame_nums, wanted_frames)
    return all_frames[condition_1]

def get_endpoint(point, angle, length):
    '''
    point - Tuple (x, y)
    angle - Angle you want your end point at in degrees.
    length - Length of the line you want to plot.
    '''
    # Unpack the first point
    x, y = point
    # Find the end point
    endy = y + (length * np.sin(np.radians(angle)))
    endx = x + (length * np.cos(np.radians(angle)))
    return endx, endy

def imgs2vid(imgs, outpath, fps):
    ''' Stitch together frame imgs to make a movie. '''
    height, width, layers = imgs[0].shape
    fourcc = cv2.VideoWriter_fourcc("m", "p", "4", "v")
    video = cv2.VideoWriter(outpath, fourcc, fps, (width, height), True)

    for img_i, img in enumerate(imgs):
        video.write(img)

    cv2.destroyAllWindows()
    video.release()

def setup_args():
    parser = argparse.ArgumentParser(description='Visualize results!')
    parser.add_argument('-p', '--data_root', dest='data_root', type=str, default='data/processed')
    parser.add_argument('-r', '--fps', dest='fps', type=int, default=30)
    args = parser.parse_args()
    return args

###### MAIN ######
def main(args, filter_bees=None):
    #------- SET FILE PATHS -------#
    # Select the video
    print("-- Select video from list...")
    src_processed_root = general_utils.select_file(args.data_root)
    print(f'\nProcessing video: {src_processed_root}')

    # Obtain up paths for video folder
    vid_name = src_processed_root.split('/')[-1]
    folder_paths = glob.glob(f'{args.data_root}/{vid_name}')
    json_paths = sorted([os.path.join(folder, f'data_log.json') for folder in folder_paths])
    frames_path = f'denoised_frames/'

    #------- PROCESS DATA -------#
    # Open json data from neural net model evaluation
    resnet_save_path = os.path.join(folder_paths[0], 'data_log_orientation.json')
    with open(resnet_save_path, 'r') as infile:
        resnet_data = json.load(infile)

    # Make data into dataframe
    resnet_df = pd.DataFrame(resnet_data)

    # Obtain first and last frames
    start_frame = resnet_df['frame_num'][0]
    end_frame = resnet_df['frame_num'][len(resnet_df['frame_num'])-1]

    # Get path of all frames & make folder to store labeled frames
    frames_path = os.path.join(folder_paths[0], f'denoised_frames/')
    all_frames = np.sort(glob.glob(f'{frames_path}frame_*.png'))
    all_wanted_frames = get_wanted_frames(start_frame, end_frame, all_frames)
    resnet_frames_path = os.path.join(folder_paths[0], f'output_frames/')
    os.makedirs(resnet_frames_path, exist_ok=True)

    data_log = json.load(open(f"{src_processed_root}/data_log.json"))

    #------- VISUALIZE SCENTING DIRECTIONS ON SCENTING BEES -------#

    prev_bee_positions = {}
    prev_scenting_directions = {}
    prev_scenting_frame = None
    max_path_length = 1200
    for frame_i, frame_path in enumerate(tqdm(all_frames, desc='Drawing Frames')):
        sys.stdout.write(f'\rDrawing frame {frame_i+1}/{len(all_frames)}')
        sys.stdout.flush()

        frame_img = cv2.imread(frame_path)
        frame_name = frame_path.split('/')[-1].split('.')[0]
        frame_num = int(frame_name.split('_')[-1])
        if frame_name not in data_log.keys():
            continue

        # cv2.line(frame_img, (1340, 20), (1460, 20), 0, 3, cv2.LINE_AA)
        # cv2.line(frame_img, (1340, 10), (1340, 30), 0, 3, cv2.LINE_AA)
        # cv2.line(frame_img, (1460, 10), (1460, 30), 0, 3, cv2.LINE_AA)
        # cv2.putText(frame_img, "5cm ", (1370, 50), cv2.FONT_HERSHEY_SIMPLEX, .8, 0, 2, cv2.LINE_AA)

        # Label the queen
        # cv2.rectangle(frame_img, (505, 150),(560, 400), COLORS[0], 2)
        # cv2.putText(frame_img, "Queen", (495, 130), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 3, cv2.LINE_AA) # black outline
        # cv2.putText(frame_img, "Queen", (495, 130), cv2.FONT_HERSHEY_SIMPLEX, .8, COLORS[0], 2, cv2.LINE_AA)

        # Draw bounding boxes, labels, and previous positions
        for bee in list(data_log[frame_name]):
            if filter_bees is not None:
                if label not in filter_bees:
                    continue
            bee_x = int(bee["x"])
            bee_y = int(bee["y"])
            bee_w = int(bee["w"])
            bee_h = int(bee["h"])
            bee_labels = [int(label) for label in bee["label"].split(',')]

            center = (int(bee_x+bee_w/2), int(bee_y+bee_h/2))
            color = COLORS[bee_labels[0]+1%6] if len(bee_labels) == 1 else (180, 180, 180)

            for label in bee_labels:
                if label not in prev_bee_positions.keys():
                    prev_bee_positions[label] = {'positions':[center], 'color':color}
                else:
                    prev_bee_positions[label]['positions'].append(center)
                # if len(prev_bee_positions[label]['positions']) > max_path_length:
                #     prev_bee_positions[label]['positions'].pop(0)

                # Draw lines connecting previous positions
                positions = prev_bee_positions[label]['positions']
                for i, position in enumerate(positions[1:]):
                    # color = cv2.cvtColor(np.uint8([[prev_bee_positions[label]['color']]]), cv2.COLOR_BGR2HSV)
                    color = prev_bee_positions[label]['color']
                    # Fade color based on age
                    # (h, s, v) = cv2.split(color)
                    # s = np.array([np.clip(s * ((i / len(positions))), 50, 255)], dtype=np.uint8) # adjust lightness based on age
                    # color = cv2.merge([h, s, v])
                    # color = cv2.cvtColor(color, cv2.COLOR_HSV2BGR)[0][0]
                    # color = (int(color[0]), int(color[1]), int(color[2]))
                    cv2.line(frame_img, position, positions[i], color, 2, cv2.LINE_AA)

        # Draw scenting direction arrows from previous frames
        for prev_dirs in prev_scenting_directions.values():
            for prev_dir in prev_dirs:
                prev_dir = prev_dir["directions"]
                if not type(prev_dir[0]) == int:
                    cv2.arrowedLine(frame_img, prev_dir[0],
                                    prev_dir[1], color=(0,0,0),
                                    thickness=3, tipLength=2) # black outline
                    cv2.arrowedLine(frame_img, prev_dir[0],
                                    prev_dir[1], color=arrow_color,
                                    thickness=2, tipLength=2)
                else:
                    # cv2.circle(frame_img, prev_dir, 2, arrow_color, -1)
                    pass

        for bee in list(data_log[frame_name]):
            bee_x = int(bee["x"])
            bee_y = int(bee["y"])
            bee_w = int(bee["w"])
            bee_h = int(bee["h"])
            labels = [int(label) for label in bee["label"].split(',')]

            # NOTE: draw box and label for each bee
            # color = COLORS[(labels[0]+1)%6] if len(labels) == 1 else (180, 180, 180)
            # image_utils.draw_box(frame_img, bee_x, bee_y, bee_w, bee_h, 2,
            #                     color=color, draw_centroid=True)
            # cv2.putText(frame_img, "Worker " + str([label+1 for label in labels]).replace("[", "").replace("]", ""), (bee_x+bee_w, bee_y+bee_h), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 3, cv2.LINE_AA) # black outline
            # cv2.putText(frame_img, "Worker " + str([label+1 for label in labels]).replace("[", "").replace("]", ""), (bee_x+bee_w, bee_y+bee_h), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 2, cv2.LINE_AA)

        # If bees are scenting, draw orientation arrow
        if frame_path in all_wanted_frames:
            # Loop over scenting bees for frame
            # Find scenting bees in df
            condition_1 = resnet_df['frame_num'] == f'frame_{frame_num:05d}'
            all_idxs = resnet_df.index[condition_1].tolist()

            condition_2 = resnet_df['classification'] == 'scenting'
            scenting_idxs = resnet_df.index[condition_1 & condition_2].tolist()

            # Draw orientation arrow on scenting bees
            for i in scenting_idxs: # all_idxs:
                x = resnet_df.at[i, 'x']    # Top left corner of bounding box
                y = resnet_df.at[i, 'y']    # Top left corner of bounding box
                w = resnet_df.at[i, 'w']    # Width of bounding box
                h = resnet_df.at[i, 'h']    # Height of bounding box
                orientation = resnet_df.at[i, 'orientation'][0]
                label = str(int(resnet_df.at[i, 'cropped_number'].split('_')[1]))

                centroid_x = int(x+w/2)
                centroid_y = int(y+h/2)

                # ========== Plot orientation arrow
                length = [35 if i in scenting_idxs else 20][0]
                thickness = [5 if i in scenting_idxs else 4][0]
                # scenting_color = (3, 252, 244)
                scenting_color = (120, 252, 120)
                non_scenting_color = (31, 194, 91)
                arrow_color = [scenting_color if i in scenting_idxs else non_scenting_color][0]

                # Centroid is midpoint, arrow points:
                midpoint_x = centroid_x
                midpoint_y = centroid_y
                pred_endx, pred_endy = get_endpoint((midpoint_x, midpoint_y), angle=-int(orientation), length=length//2)
                pred_x1, pred_y1 = get_endpoint((midpoint_x, midpoint_y), angle=-int(orientation)+180, length=length//2)
                pred_endx2, pred_endy2 = get_endpoint((midpoint_x, midpoint_y), angle=-int(orientation), length=5)
                pred_x2, pred_y2 = get_endpoint((midpoint_x, midpoint_y), angle=-int(orientation)+180, length=5)

                # Plot arrows
                # cv2.arrowedLine(frame_img, (int(pred_endx), int(pred_endy)),
                #                 (int(pred_x1), int(pred_y1)), color=(0, 0, 255),
                #                 thickness=2, tipLength=0.6)

                # save scenting direction
                # if prev_scenting_frame is not None:
                if label in prev_scenting_directions.keys():
                    # prev_frame_num = int(prev_scenting_frame.split('/')[-1].split('.')[0].split('_')[-1])
                    prev_pos = prev_scenting_directions[label][-1]["directions"]
                    if not type(prev_pos[0]) == int:
                        prev_pos = prev_pos[0]
                    distance = math.sqrt((centroid_x - prev_pos[0])**2 + (centroid_y - prev_pos[1])**2)
                    if distance > 10:
                        prev_scenting_directions[label].append({"frame":frame_i, "directions":((int(pred_endx2), int(pred_endy2)),
                                        (int(pred_x2), int(pred_y2)))})
                    else:
                        prev_scenting_directions[label].append({"frame":frame_i, "directions":(int(centroid_x), int(centroid_y))})
                else:
                    prev_scenting_directions[label] = [{"frame":frame_i, "directions":((int(pred_endx2), int(pred_endy2)),
                                        (int(pred_x2), int(pred_y2)))}]

        # NOTE: Remove old scenting directions once the path is too long
        for prev_dir in prev_scenting_directions.values():
            if len(prev_dir) > 1:
                # print("prev_dir", prev_dir[0])
                # while frame_i - prev_dir[0]["frame"] > max_path_length:
                #     prev_dir.pop(0)
                # prev_scenting_frame = frame_path
                pass

        cv2.imshow('frame', frame_img)
        k = cv2.waitKey(30) & 0xff
        if k == 27:
            break

        # Write frame to file
        save_path = f'{resnet_frames_path}/frame_{frame_num:05d}.png'
        cv2.imwrite(save_path, frame_img)
    cv2.destroyAllWindows()

    #------- MAKE MOVIE FROM FRAMES -------#
    print('\nMaking movie...')
    all_img_paths = np.sort(glob2.glob(f"{folder_paths[0]}/output_frames/*.png"))
    print("all paths", all_img_paths)
    all_imgs = np.array([cv2.imread(img) for img in all_img_paths])
    save_title = 'output_movie_annotated_short_trails'
    savepath = f'{folder_paths[0]}/{save_title}.mp4'
    imgs2vid(all_imgs, savepath, args.fps)
    print('Fin.\n')

def create_helper_dirs(data_root, dirname):
    # Create Directories
    drawn_frames_dir = general_utils.make_directory(
        dirname, root=data_root, remove_old=True)

    return drawn_frames_dir

def read_in_frames(denoised_frames_dir):
    denoised_filepaths = np.sort(
        glob.glob(f'{denoised_frames_dir}/**/denoised*/*.png', recursive=True))
    return denoised_filepaths

if __name__ == '__main__':
    args = setup_args()
    main(args, filter_bees=None)
