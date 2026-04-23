from flask import Flask, jsonify, render_template, request, Response
from minio import Minio
from minio.error import S3Error

from config import Config
from database import Database

app = Flask(__name__)
config = Config()
db = Database(config)

minio_client = Minio(
    endpoint=config.minio_endpoint,
    access_key=config.minio_access_key,
    secret_key=config.minio_secret_key,
    secure=config.minio_secure,
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/notices')
def get_notices():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    sort_by = request.args.get('sort_by', 'last_updated')
    sort_order = request.args.get('sort_order', 'desc')

    filters = {
        'search': request.args.get('search'),
        'nationality': request.args.get('nationality'),
        'eye_color': request.args.get('eye_color'),
        'has_criminal_record': request.args.get('has_criminal_record'),
        'dob_from': request.args.get('dob_from'),
        'dob_to': request.args.get('dob_to'),
    }

    total = db.get_notice_count(filters)
    items = db.get_notices(filters, page, page_size, sort_by, sort_order)

    for item in items:
        if item.get('primary_photo_key'):
            item['photo_url'] = f"/api/photos/{item['entity_id']}"
        else:
            item['photo_url'] = None

    return jsonify({
        'page': page,
        'page_size': page_size,
        'total': total,
        'items': items,
    })

@app.route('/api/updates')
def get_updates():
    return jsonify(db.get_recent_updates(limit=50))


@app.route('/api/photos/<entity_id>')
def proxy_photo(entity_id):
    photo = db.get_primary_photo(entity_id)
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404

    object_key = photo['object_key']
    content_type = photo.get('content_type') or 'image/jpeg'

    try:
        obj = minio_client.get_object(config.minio_bucket, object_key)
        data = obj.read()
        obj.close()
        obj.release_conn()
        return Response(data, mimetype=content_type)
    except S3Error as exc:
        return jsonify({'error': f'MinIO error: {str(exc)}'}), 404
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500

if __name__ == '__main__':
    print('Initializing web server: http://0.0.0.0:', config.web_port)
    app.run(host='0.0.0.0', port=config.web_port)