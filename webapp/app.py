import cherrypy
import boto3
import jinja2
import os
import os.path
import mimetypes
import mpd

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates/')
STATIC_DIR = os.path.join(BASE_DIR, 'static/')
CONF_DIR = os.path.join(BASE_DIR, 'conf/')

s3 = boto3.client('s3')

tenv = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
                          autoescape=jinja2.select_autoescape(['html', 'xml']))

KNOWN_TYPES = {
    'audio/mp3': '.mp3',
    'audio/ogg': '.ogg',
    'audio/aac': '.aac',
}

def guess_extension(media_type):
    try:
        return KNOWN_TYPES[media_type.lower()]
    except KeyError:
        pass

    ext = mimetypes.guess_extension(media_type, False)
    return ext if ext else ''

class MusicUpload(object):
    @cherrypy.expose
    def index(self):
        template = tenv.get_template('music/index.html')
        return template.render()

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def update(self, key):
        config = cherrypy.request.app.config['music_upload']
        library = config['library_dir']
        mpd_host = config['mpd_host']
        mpd_port = config['mpd_port']

        path = os.path.join(library, key)
        real_library = os.path.realpath(library)
        real_path = os.path.realpath(path)

        if not real_path.startswith(real_library) or not os.path.isfile(path):
            raise cherrypy.HTTPError(404, 'File does not exist (yet.)')

        client = mpd.MPDClient(use_unicode=True)
        client.connect(mpd_host, mpd_port)
        try:
            client.update(key)
            client.disconnect()
            cherrypy.response.status = 204
        finally:
            client.disconnect()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def s3(self, artist, album, title, media_type):
        bucket = cherrypy.request.app.config['music_upload']['bucket']
        filename = ' - '.join([artist, title]) + guess_extension(media_type)
        key = '/'.join([x for x in (artist, album, filename) if x])
        presigned = s3.generate_presigned_post(
            Bucket = bucket,
            Key = key,
            Fields = {'Content-Type': media_type,
                      'x-amz-storage-class': 'REDUCED_REDUNDANCY'},
            Conditions = [{'Content-Type': media_type},
                          {'x-amz-storage-class': 'REDUCED_REDUNDANCY'},
                          ['content-length-range', 0, 100*1024*1024]],
            ExpiresIn = 3600
        )
        return {
            'key': key,
            'data': presigned
        }

if __name__ == '__main__':
    conf = {
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': STATIC_DIR,
        },
    }

    app = cherrypy.tree.mount(MusicUpload(), '/', conf)

    try:
        local = os.path.join(CONF_DIR, 'local.conf')
        cherrypy.config.update(local)
        app.merge(local)
    except FileNotFoundError:
        pass

    cherrypy.engine.start()
    cherrypy.engine.block()
