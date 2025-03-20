import os
import requests
import traceback
import time
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Video, Player
import logging
import magic
from urllib.parse import urlparse, parse_qs

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
video_bp = Blueprint('video', __name__)

# Configure upload settings
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'ogg'}
ALLOWED_MIME_TYPES = {
    'video/mp4',
    'video/webm',
    'video/ogg',
    'application/octet-stream'  # Some video files might be detected as this
}

def get_upload_folder():
    upload_folder = os.path.join(current_app.root_path, 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_youtube_url(url):
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        return 'v' in parse_qs(parsed.query)
    elif 'youtu.be' in parsed.netloc:
        return bool(parsed.path[1:])
    return False

def get_youtube_video_id(url):
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        query = parse_qs(parsed.query)
        return query.get('v', [None])[0]
    elif 'youtu.be' in parsed.netloc:
        return parsed.path[1:]
    return None

@video_bp.route('/api/players/<int:player_id>/videos', methods=['POST'])
@login_required
def upload_video(player_id):
    try:
        logger.debug(f"Video upload requested for player {player_id}")
        logger.debug(f"Form data: {request.form}")
        logger.debug(f"Files: {request.files}")

        # Check if player exists and belongs to current user
        player = Player.query.filter_by(id=player_id, user_id=current_user.id).first()
        if not player:
            logger.warning(f"Player {player_id} not found or unauthorized for user {current_user.id}")
            return jsonify({'error': 'Player not found or unauthorized'}), 404

        # Get basic video info
        if 'title' not in request.form:
            logger.warning("Missing title in form data")
            return jsonify({'error': 'Video title is required'}), 400

        source_type = request.form.get('source_type', 'file')
        filename = None
        file_path = None

        # Get video metadata
        action_type = request.form.get('action_type')
        skill_rating = request.form.get('skill_rating', type=int)
        tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
        notes = request.form.get('notes', '')

        try:
            if source_type == 'file':
                logger.debug("Processing file upload")
                if 'video' not in request.files:
                    return jsonify({'error': 'No video file provided'}), 400

                file = request.files['video']
                if file.filename == '':
                    return jsonify({'error': 'No selected file'}), 400

                if not allowed_file(file.filename):
                    return jsonify({'error': 'File type not allowed'}), 400

                filename = secure_filename(file.filename)
                file_path = os.path.join(get_upload_folder(), filename)
                logger.debug(f"Saving file to: {file_path}")
                file.save(file_path)

                # Create video record for file
                video = Video(
                    title=request.form['title'],
                    filename=filename,
                    video_type='file',
                    player_id=player_id,
                    user_id=current_user.id,
                    filesize=os.path.getsize(file_path),
                    action_type=action_type,
                    skill_rating=skill_rating,
                    tags=tags,
                    notes=notes
                )

            else:  # source_type == 'url'
                logger.debug("Processing URL upload")
                if 'video_url' not in request.form:
                    return jsonify({'error': 'No video URL provided'}), 400

                video_url = request.form['video_url']
                if not is_youtube_url(video_url):
                    return jsonify({'error': 'Only YouTube URLs are supported'}), 400

                youtube_id = get_youtube_video_id(video_url)
                if not youtube_id:
                    return jsonify({'error': 'Invalid YouTube URL'}), 400

                # Create video record for YouTube
                video = Video(
                    title=request.form['title'],
                    video_url=video_url,
                    video_type='youtube',
                    youtube_id=youtube_id,
                    player_id=player_id,
                    user_id=current_user.id,
                    action_type=action_type,
                    skill_rating=skill_rating,
                    tags=tags,
                    notes=notes
                )

            db.session.add(video)
            db.session.commit()

            logger.info(f"Video record created successfully: {video.id}")
            response = jsonify({
                'message': 'Video added successfully',
                'video': {
                    'id': video.id,
                    'title': video.title,
                    'type': video.video_type,
                    'youtube_id': video.youtube_id if video.video_type == 'youtube' else None,
                    'filename': video.filename if video.video_type == 'file' else None,
                    'upload_date': video.upload_date.isoformat(),
                    'action_type': video.action_type,
                    'skill_rating': video.skill_rating,
                    'tags': video.tags,
                    'notes': video.notes
                }
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 201

        except Exception as e:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            error_msg = f"Error during video processing: {repr(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return jsonify({'error': str(e) or 'An unexpected error occurred during video processing'}), 500

    except Exception as e:
        error_msg = f"Error uploading video: {repr(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': str(e) or 'An unexpected error occurred during upload'}), 500

@video_bp.route('/api/players/<int:player_id>/videos/<int:video_id>', methods=['GET'])
@login_required
def get_video(player_id, video_id):
    try:
        video = Video.query.get_or_404(video_id)

        # Check if user has access to this video
        if video.player_id != player_id or video.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        if video.video_type == 'file':
            return send_from_directory(get_upload_folder(), video.filename)
        elif video.video_type == 'youtube':
            return jsonify({'url': video.video_url}) # Return YouTube URL instead of file
        else:
            return jsonify({'error': 'Unknown video type'}), 500

    except Exception as e:
        logger.error(f"Error serving video: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@video_bp.route('/api/players/<int:player_id>/videos', methods=['GET'])
@login_required
def get_player_videos(player_id):
    try:
        # Check if player exists and belongs to current user
        player = Player.query.filter_by(id=player_id, user_id=current_user.id).first()
        if not player:
            return jsonify({'error': 'Player not found or unauthorized'}), 404

        videos = Video.query.filter_by(player_id=player_id).all()
        videos_data = [{
            'id': video.id,
            'title': video.title,
            'type': video.video_type,
            'youtube_id': video.youtube_id if video.video_type == 'youtube' else None,
            'filename': video.filename if video.video_type == 'file' else None,
            'upload_date': video.upload_date.isoformat(),
            'duration': video.duration,
            'filesize': video.filesize
        } for video in videos]

        return jsonify(videos_data)

    except Exception as e:
        logger.error(f"Error fetching videos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500