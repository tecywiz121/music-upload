(function() {
    'use strict';

    let file = document.getElementById('file'),
        artist = document.getElementById('artist'),
        album = document.getElementById('album'),
        title = document.getElementById('title'),
        form = document.getElementById('upload-form'),
        fieldset = form.firstElementChild;

    /*
     * Auto-populate the Artist, Album, and Title fields from the ID3 tags.
     */
    file.addEventListener('change', () => {
        let savedArtist = artist.value,
            savedAlbum = album.value,
            savedTitle = album.title;

        if (!file.files[0]) {
            return;
        }

        new jsmediatags.Reader(file.files[0])
            .setTagsToRead(['title', 'artist', 'album'])
            .read({
                onSuccess: (tag) => {
                    if (savedArtist === artist.value) {
                        artist.value = tag.tags.artist || '';
                    }

                    if (savedAlbum === album.value) {
                        album.value = tag.tags.album || '';
                    }

                    if (savedTitle === title.value) {
                        title.value = tag.tags.title || '';
                    }
                }
            });
    });

    let mpdUpdate = function(key) {
        let xhr = new XMLHttpRequest(),
            postData = new FormData();

        postData.append('key', key);
        xhr.open('POST', 'update/');
        xhr.send(postData);
    };

    let s3Upload = function(response, key) {
        let xhr = new XMLHttpRequest(),
            postData = new FormData();

        for (let key in response.fields) {
            postData.append(key, response.fields[key]);
        }

        postData.append('file', file.files[0]);

        xhr.open('POST', response.url);

        xhr.onreadystatechange = () => {
            if (4 !== xhr.readyState) {
                return;
            }

            if (200 !== xhr.status && 204 !== xhr.status) {
                fieldset.disabled = false;
                alert('Could not upload file.');
                return;
            }

            form.reset();
            fieldset.disabled = false;
            mpdUpdate(key);
        };

        xhr.send(postData);
    };

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        fieldset.disabled = true;

        let xhr = new XMLHttpRequest(),
            artistEnc = encodeURIComponent(artist.value),
            albumEnc = encodeURIComponent(album.value),
            titleEnc = encodeURIComponent(title.value),
            typeEnc = encodeURIComponent(file.files[0].type);

        xhr.open(
            'GET',
            `s3/?artist=${artistEnc}&album=${albumEnc}&title=${titleEnc}&media_type=${typeEnc}`
        );

        xhr.onreadystatechange = () => {
            if (4 !== xhr.readyState) {
                return;
            }

            if (200 !== xhr.status) {
                fieldset.disabled = false;
                alert('Could not get policy for s3 upload.');
                return;
            }

            let response = JSON.parse(xhr.responseText);
            s3Upload(response.data, response.key);
        };

        xhr.send();
    });
}());
