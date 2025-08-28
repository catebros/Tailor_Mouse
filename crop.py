import streamlit as st
import os
import ffmpeg
import zipfile
from streamlit_cropper import st_cropper
from PIL import Image
import tempfile


def crop(temp_file_paths):
    if not temp_file_paths:
        st.error("No files provided")
        return

    ZIP_THRESHOLD_MB = 500  # Zip

    try:
        if 'crop_settings' not in st.session_state:
            st.session_state.crop_settings = {}

        if 'frame_images' not in st.session_state:
            st.session_state.frame_images = {}

        if 'video_durations' not in st.session_state:
            st.session_state.video_durations = {}

        st.header(f"Uploaded Files ({len(temp_file_paths)})")
        
        st.sidebar.title("Crop Configuration")
        
        st.sidebar.header("1. Video & Mouse Setup")
        
        st.sidebar.subheader("Video Selection")
        selected_idx = st.sidebar.selectbox(
            "Choose a video:",
            range(len(temp_file_paths)),
            format_func=lambda i: os.path.basename(temp_file_paths[i])
        )

        selected_video_path = temp_file_paths[selected_idx]
        selected_video_name = os.path.basename(selected_video_path)

        st.sidebar.subheader("Mouse IDs Setup")
        
        saved_mouse_ids = []
        if selected_video_name in st.session_state.crop_settings:
            saved_mouse_ids = [int(mid) for mid in st.session_state.crop_settings[selected_video_name].keys() if mid.isdigit()]
        
        input_key = f"mouse_ids_{selected_video_name}"
        
        if input_key in st.session_state and st.session_state[input_key]:
            default_mouse_ids_str = st.session_state[input_key]
        else:
            default_mouse_ids_str = ",".join(map(str, saved_mouse_ids)) if saved_mouse_ids else ""
        
        mouse_ids_input = st.sidebar.text_input(
            "Enter mouse IDs in the video (comma-separated) - Example: 1,2,3", 
            value=default_mouse_ids_str,
            key=input_key
        )
        mouse_ids = [int(m.strip()) for m in mouse_ids_input.split(",") if m.strip().isdigit()]

        if not mouse_ids:
            st.sidebar.warning("Please enter at least one mouse ID.")
            return

        if selected_video_name not in st.session_state.crop_settings:
            st.session_state.crop_settings[selected_video_name] = {}

        current_crop_keys = list(st.session_state.crop_settings[selected_video_name].keys())
        for existing_mouse_id in current_crop_keys:
            if existing_mouse_id not in [str(m) for m in mouse_ids]:
                del st.session_state.crop_settings[selected_video_name][existing_mouse_id]

        for mid in mouse_ids:
            if str(mid) not in st.session_state.crop_settings[selected_video_name]:
                st.session_state.crop_settings[selected_video_name][str(mid)] = None

        def render_file_info_table():
            file_info_data = []
            for path in temp_file_paths:
                file_name = os.path.basename(path)
                try:
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                except:
                    size_mb = 0

                try:
                    if file_name not in st.session_state.video_durations:
                        duration_val = float(ffmpeg.probe(path)['format']['duration'])
                        st.session_state.video_durations[file_name] = duration_val
                    else:
                        duration_val = st.session_state.video_durations[file_name]
                    duration_str = f"{duration_val:.1f}s"
                except:
                    duration_str = "Unknown"

                crops_dict = st.session_state.crop_settings.get(file_name, {})
                
                if file_name == selected_video_name:
                    total_crops = len(mouse_ids)
                    set_mice = []
                    for m in sorted(mouse_ids):
                        if crops_dict.get(str(m)) is not None:
                            set_mice.append(f"Mouse {m}")
                    crops_set = len(set_mice)
                else:
                    crops_set = sum(1 for c in crops_dict.values() if c is not None)
                    total_crops = len(crops_dict) if crops_dict else 0
                    set_mice = [f"Mouse {m}" for m in sorted([int(mid) for mid in crops_dict.keys() if mid.isdigit()]) if crops_dict[str(m)] is not None]
                
                if set_mice:
                    crops_detail = f"{crops_set}/{total_crops} ({', '.join(set_mice)})"
                else:
                    crops_detail = f"{crops_set}/{total_crops}"

                file_info_data.append({
                    "File Name": file_name,
                    "Size (MB)": f"{size_mb:.1f}",
                    "Duration": duration_str,
                    "Crops Set": crops_detail
                })

            st.dataframe(file_info_data, use_container_width=True, hide_index=True)

        render_file_info_table()

        st.sidebar.markdown("---")
        
        st.sidebar.header("2. Frame Extraction & Cropping")

        selected_mouse_id = st.sidebar.selectbox("Select mouse to crop", mouse_ids, format_func=lambda x: f"Mouse {x}")

        try:
            if selected_video_name not in st.session_state.video_durations:
                duration = float(ffmpeg.probe(selected_video_path)['format']['duration'])
                st.session_state.video_durations[selected_video_name] = duration
            else:
                duration = st.session_state.video_durations[selected_video_name]
        except:
            duration = 10.0

        frame_key = f"frame_time_{selected_video_name}"
        if frame_key not in st.session_state:
            st.session_state[frame_key] = duration / 2

        st.sidebar.subheader("Frame Selection")
        frame_time = st.sidebar.slider(
            "Select time (seconds)",
            min_value=0.0,
            max_value=duration - 1,
            value=st.session_state[frame_key],
            step=0.1,
            key=f"slider_{selected_video_name}"
        )

        if st.sidebar.button("Extract Frame", key=f"extract_{selected_video_name}"):
            temp_frame_path = tempfile.mktemp(suffix='.jpg')
            try:
                (
                    ffmpeg
                    .input(selected_video_path, ss=frame_time)
                    .output(temp_frame_path, vframes=1, format='image2', vcodec='mjpeg')
                    .overwrite_output()
                    .run(quiet=True)
                )
                frame_image = Image.open(temp_frame_path)
                st.session_state.frame_images[selected_video_name] = frame_image.copy()
                st.session_state[f"frame_extracted_{selected_video_name}"] = True
                frame_image.close()
            except Exception as e:
                st.error(f"Error extracting frame: {str(e)}")
            finally:
                if os.path.exists(temp_frame_path):
                    os.unlink(temp_frame_path)

        if st.session_state.get(f"frame_extracted_{selected_video_name}", False):
            st.subheader(f"Draw Crop Box for Mouse {selected_mouse_id}")
            crop_box = st_cropper(
                st.session_state.frame_images[selected_video_name],
                realtime_update=True,
                box_color='#0000FF',
                aspect_ratio=None,
                return_type='box',
            )

            if st.button("Set Crop for This Mouse"):
                try:
                    if crop_box and all(k in crop_box for k in ['left', 'top', 'width', 'height']):
                        crop_data = {
                            'x': int(round(crop_box['left'])),
                            'y': int(round(crop_box['top'])),
                            'w': int(round(crop_box['width'])),
                            'h': int(round(crop_box['height']))
                        }
                        
                        if selected_video_name not in st.session_state.crop_settings:
                            st.session_state.crop_settings[selected_video_name] = {}
                        
                        st.session_state.crop_settings[selected_video_name][str(selected_mouse_id)] = crop_data
                        st.success(f"Crop set for Mouse {selected_mouse_id} in {selected_video_name}")
                        st.rerun()
                    else:
                        st.error("Please draw a valid crop box before setting the crop.")
                except Exception as e:
                    st.error(f"Error setting crop: {str(e)}")

        st.sidebar.markdown("---")
        
        st.sidebar.header("3. Output Configuration")
        
        st.sidebar.subheader("Output Folder")
        OUTPUT_DIR = st.sidebar.text_input("Full output folder path", os.path.join(os.path.expanduser("~"), "Videos", "Cropped"))
        
        folder_exists = os.path.exists(OUTPUT_DIR)
        if folder_exists:
            existing_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp4')]
            if existing_files:
                st.sidebar.warning(f"Folder exists with {len(existing_files)} video files!")
                overwrite_option = st.sidebar.radio(
                    "What to do with existing files?",
                    ["Overwrite existing files", "Create new folder with timestamp"],
                    index=1
                )
            else:
                overwrite_option = "Overwrite existing files"
        else:
            overwrite_option = "Overwrite existing files"
        
        if overwrite_option == "Create new folder with timestamp" and folder_exists:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_output_dir = f"{OUTPUT_DIR}_{timestamp}"
            st.sidebar.info(f"Will create: {os.path.basename(final_output_dir)}")
        else:
            final_output_dir = OUTPUT_DIR

        st.sidebar.subheader("File Naming")
        
        if "prefix_settings" not in st.session_state:
            st.session_state.prefix_settings = {}
        
        for path in temp_file_paths:
            video_name = os.path.basename(path)
            if video_name not in st.session_state.prefix_settings:
                default_prefix = video_name.split('_')[0] if '_' in video_name else os.path.splitext(video_name)[0]
                st.session_state.prefix_settings[video_name] = default_prefix
        
        st.sidebar.markdown("**Customize output prefixes:**")
        
        all_prefixes = []
        duplicate_found = False
        potential_conflicts = []
        
        for path in temp_file_paths:
            video_name = os.path.basename(path)
            current_prefix = st.session_state.prefix_settings[video_name]
            
            new_prefix = st.sidebar.text_input(
                f"Prefix for {video_name}:",
                value=current_prefix,
                key=f"prefix_{video_name}"
            )
            
            if new_prefix != current_prefix:
                st.session_state.prefix_settings[video_name] = new_prefix
            
            st.sidebar.caption(f"{new_prefix}_mouseX.mp4")
            
            all_prefixes.append(new_prefix)

        from collections import defaultdict
        potential_filenames = defaultdict(list)
        
        for path in temp_file_paths:
            video_name = os.path.basename(path)
            video_prefix = st.session_state.prefix_settings[video_name]
            
            if video_name == selected_video_name:
                current_mouse_ids = mouse_ids
            else:
                crops_dict = st.session_state.crop_settings.get(video_name, {})
                current_mouse_ids = [int(mid) for mid in crops_dict.keys() if crops_dict[mid] is not None]
            
            for mouse_id in current_mouse_ids:
                filename = f"{video_prefix}_mouse{mouse_id}.mp4"
                potential_filenames[filename].append(video_name)

        conflicts = {fname: videos for fname, videos in potential_filenames.items() if len(videos) > 1}
        
        if conflicts:
            st.sidebar.error("Filename conflicts detected! Multiple videos will create the same output files.")
            for filename, videos in conflicts.items():
                st.sidebar.error(f"**{filename}** will be created by: {', '.join(videos)}")
            
            st.sidebar.subheader("Solutions:")
            st.sidebar.info("Please ensure each video has a unique prefix, or use different mouse IDs for videos with the same prefix.")
            duplicate_found = True

        st.sidebar.markdown("---")
        
        st.sidebar.header("4. Process Videos")

        if duplicate_found:
            st.sidebar.error("Please fix filename conflicts before processing")
            process_button_disabled = True
        else:
            process_button_disabled = False

        if st.sidebar.button("Crop All Videos", use_container_width=True, disabled=process_button_disabled):
            os.makedirs(final_output_dir, exist_ok=True)
            
            st.session_state[f"frame_extracted_{selected_video_name}"] = False
            st.session_state["processing_started"] = True

            if not st.session_state.crop_settings:
                st.sidebar.warning("No crops have been set.")
            else:
                st.subheader("Cropping Process")
                output_files = []
                
                used_filenames = set()

                for video_idx, video_path in enumerate(temp_file_paths):
                    video_name = os.path.basename(video_path)
                    
                    video_prefix = st.session_state.prefix_settings.get(video_name, video_name.split('_')[0] if '_' in video_name else os.path.splitext(video_name)[0])
                    
                    if video_name == selected_video_name:
                        current_mouse_ids = mouse_ids  
                    else:
                        crops_dict = st.session_state.crop_settings.get(video_name, {})
                        current_mouse_ids = [int(mid) for mid in crops_dict.keys() if crops_dict.get(mid) is not None]
                    
                    if not current_mouse_ids:
                        st.warning(f"Skipping {video_name}: No mouse crops defined.")
                        continue

                    st.write(f"**Processing {video_name}** with mice: {current_mouse_ids}")

                    for mouse_id in current_mouse_ids:
                        crop_data = st.session_state.crop_settings.get(video_name, {}).get(str(mouse_id))
                        
                        if not crop_data:
                            st.warning(f"Skipping {video_name} Mouse {mouse_id}: no crop defined.")
                            continue

                        base_filename = f'{video_prefix}_mouse{mouse_id}.mp4'
                        output_filename = base_filename
                        counter = 1
                        
                        while output_filename in used_filenames:
                            name_without_ext = os.path.splitext(base_filename)[0]
                            output_filename = f"{name_without_ext}_{counter}.mp4"
                            counter += 1
                        
                        used_filenames.add(output_filename)
                        output_file = os.path.join(final_output_dir, output_filename)

                        st.write(f"**{video_name} (Mouse {mouse_id})** → {output_filename}")
                        st.write(f"Cropping to {crop_data['w']}x{crop_data['h']} at ({crop_data['x']}, {crop_data['y']})")

                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        status_text.info(f"Processing {video_name} Mouse {mouse_id}...")

                        try:
                            (
                                ffmpeg
                                .input(video_path)
                                .filter('crop', crop_data['w'], crop_data['h'], crop_data['x'], crop_data['y'])
                                .output(output_file, vcodec='libx264', acodec='aac', an=None)
                                .overwrite_output()
                                .run(quiet=True)
                            )

                            output_files.append(output_file)
                            progress_bar.progress(1.0)
                            status_text.success(f"Completed {video_name} Mouse {mouse_id}")

                        except Exception as e:
                            status_text.error(f"Error cropping {video_name} Mouse {mouse_id}: {str(e)}")

                        st.write("---")

                st.write(f"**Total files processed: {len(output_files)}**")

                total_size_mb = sum(os.path.getsize(f) for f in output_files) / (1024 * 1024)
                if total_size_mb >= ZIP_THRESHOLD_MB:
                    zip_name = os.path.basename(os.path.normpath(final_output_dir)) + ".zip"
                    zip_path = os.path.join(final_output_dir, zip_name)                  
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for f in output_files:
                            zipf.write(f, os.path.basename(f))
                    st.success(f"Files zipped to: {zip_path}")
                else:
                    st.success(f"All videos saved to: {final_output_dir}")

    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
