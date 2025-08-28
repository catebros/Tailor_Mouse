import streamlit as st
import os
from pathlib import Path
from trim import trim
from crop import crop
from crop_trim import crop_trim

st.set_page_config(page_title="Video Processing", layout="wide", page_icon="data/image.jpg")

st.title('Video Processing')

def get_video_files_tree(root_path):
    """Get hierarchical structure of video files"""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    tree = {}
    
    try:
        root = Path(root_path)
        if not root.exists():
            return {}
            
        for item in root.rglob('*'):
            if item.is_file() and item.suffix.lower() in video_extensions:
                parts = item.relative_to(root).parts

                current = tree
                for part in parts[:-1]: 
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                if '_files' not in current:
                    current['_files'] = []
                current['_files'].append({
                    'name': parts[-1],
                    'path': str(item),
                    'size': item.stat().st_size / (1024**2)  
                })
    except Exception as e:
        st.error(f"Error scanning directory: {e}")
        return {}
    
    return tree

def render_directory_tree(tree, path_prefix="", level=0):
    """Render the directory tree with checkboxes"""
    selected_files = []
    
    for key, value in tree.items():
        if key == '_files':
            if value: 
                st.write("📁 **Files in this directory:**")
                for file_info in value:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        is_selected = st.checkbox(
                            f"🎬 {file_info['name']}", 
                            key=f"file_{file_info['path']}"
                        )
                    with col2:
                        st.write(f"{file_info['size']:.1f} MB")
                    with col3:
                        if st.button("ℹ️", key=f"info_{file_info['path']}", help="File info"):
                            st.info(f"Path: {file_info['path']}")
                    
                    if is_selected:
                        selected_files.append(file_info['path'])
        else:
            indent = "　" * level
            
            folder_key = f"folder_{path_prefix}_{key}"
            if folder_key not in st.session_state:
                st.session_state[folder_key] = level < 2  
            
            col1, col2 = st.columns([6, 1])
            with col1:
                st.write(f"{indent}📂 **{key}**")
            with col2:
                if st.button("📁" if st.session_state[folder_key] else "📂", 
                           key=f"toggle_{folder_key}", 
                           help="Expand/Collapse"):
                    st.session_state[folder_key] = not st.session_state[folder_key]
                    st.rerun()
            
            if st.session_state[folder_key]:
                with st.container():
                    st.markdown(f'<div style="margin-left: {(level + 1) * 20}px; border-left: 2px solid #f0f0f0; padding-left: 10px;">', 
                              unsafe_allow_html=True)
                    sub_selected = render_directory_tree(value, f"{path_prefix}/{key}", level + 1)
                    selected_files.extend(sub_selected)
                    st.markdown('</div>', unsafe_allow_html=True)
    
    return selected_files

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'selected_files_for_processing' not in st.session_state:
    st.session_state.selected_files_for_processing = []
if 'processing_type' not in st.session_state:
    st.session_state.processing_type = ""

if st.session_state.processing:
    st.header('Processing Videos')
    
    selected_files = st.session_state.selected_files_for_processing
    processing_type = st.session_state.processing_type
    
    st.info(f"Processing {len(selected_files)} files with **{processing_type}** operation")
    
    with st.container():
        st.subheader("Files being processed:")
        
        for i, file_path in enumerate(selected_files):
            col_file1, col_file2 = st.columns([3, 1])
            with col_file1:
                st.write(f"**{i+1}.** `{os.path.basename(file_path)}`")
            with col_file2:
                st.write(f"{os.path.dirname(file_path)}")
    
    st.markdown("---")
    
    try:
        progress_container = st.empty()
        
        if processing_type == 'Crop':
            crop(selected_files)
        elif processing_type == 'Trim':
            trim(selected_files)
        elif processing_type == 'Crop and Trim':
            crop_trim(selected_files)
        
        
        col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
        with col_back2:
            if st.button("Back to File Browser", type="primary", use_container_width=True):
                st.session_state.processing = False
                st.session_state.selected_files_for_processing = []
                st.session_state.current_path = st.session_state.get('last_path', "/home/user/videos")
                st.rerun()
            

    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        
        col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
        with col_back2:
            if st.button("Back to File Browser", type="primary", use_container_width=True):
                st.session_state.processing = False
                st.session_state.selected_files_for_processing = []
                st.session_state.current_path = st.session_state.get('last_path', "/home/user/videos")
                st.rerun()

else:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header('Processing Options')
        crop_trim_selected = st.radio('Processing Options', ['Crop', 'Trim', 'Crop and Trim'])
        
        st.header('Directory Settings')
        
        default_path = st.text_input(
            "Root directory path:", 
            value="/home/user/videos",
            help="Enter the root path to scan for video files"
        )
        
        scan_button = st.button("Scan Directory", type="primary")

    with col2:
        st.header('Video File Browser')
        
        if 'current_path' not in st.session_state:
            st.session_state.current_path = default_path
        
        if scan_button:
            st.session_state.current_path = default_path
        
        current_path = st.session_state.current_path
        
        if current_path:
            
            with st.spinner("Scanning directory..."):
                video_tree = get_video_files_tree(current_path)
            
            if video_tree:
                total_files = sum(len(d.get('_files', [])) for d in [video_tree] + 
                                [v for v in video_tree.values() if isinstance(v, dict)])
                
                def count_files_recursive(tree):
                    count = 0
                    for key, value in tree.items():
                        if key == '_files':
                            count += len(value)
                        elif isinstance(value, dict):
                            count += count_files_recursive(value)
                    return count
                
                total_files = count_files_recursive(video_tree)
                
                st.subheader("Select Videos to Process")
                
                col_a, col_b, col_c = st.columns([1, 1, 2])
                with col_a:
                    if st.button("Select All"):
                        st.info("Use individual checkboxes to select files")
                with col_b:
                    if st.button("Clear All"):
                        st.rerun()
                
                selected_files = render_directory_tree(video_tree)
                
                if selected_files:
                    st.success(f"Selected {len(selected_files)} files for processing")
                    
                    with st.expander("Selected Files", expanded=False):
                        for i, file_path in enumerate(selected_files, 1):
                            st.write(f"{i}. `{file_path}`")
                    
                    if st.button("Process Selected Files", type="primary"):
                        st.session_state.last_path = current_path
                        st.session_state.processing = True
                        st.session_state.selected_files_for_processing = selected_files.copy()
                        st.session_state.processing_type = crop_trim_selected
                        st.rerun()
                else:
                    st.info("Select video files using the checkboxes above")
                    
            else:
                st.warning("No video files found in the specified directory")
                st.info("Supported formats: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V")
        else:
            st.info("Enter a directory path and click 'Scan Directory'")
