from unittest.mock import Mock

import pytest

from src.utils.playlist_reference import load_reference, reference_sample, reference_songs


def _track(track_id, name, artist):
    return {
        'id': track_id,
        'name': name,
        'type': 'track',
        'artists': [{'name': artist}],
    }


def test_load_reference_reads_all_pages_and_skips_unusable_items():
    spotify = Mock()
    spotify._get.side_effect = [
        {
            'items': [
                {'item': _track('one', 'Uno', 'A')},
                {'item': None},
                {'item': {'id': 'episode', 'type': 'episode', 'artists': []}},
            ],
            'next': 'next-page',
        },
        {
            'items': [
                {'track': _track('two', 'Dos', 'B')},
                {'track': _track('one', 'Uno', 'A')},
            ],
            'next': None,
        },
    ]

    tracks = load_reference(spotify, 'playlist-id')

    assert [track['id'] for track in tracks] == ['one', 'two']
    assert spotify._get.call_args_list[1].kwargs['offset'] == 3


def test_reference_helpers_preserve_multi_artist_names_and_bound_sample():
    tracks = [
        _track(str(index), f'Canción {index}', f'Artista {index}')
        for index in range(101)
    ]
    tracks[50]['artists'].append({'name': 'Invitado'})

    assert reference_songs(tracks[:1]) == [{'title': 'Canción 0', 'artist': 'Artista 0'}]
    assert reference_songs([tracks[50]])[0]['artist'] == 'Artista 50, Invitado'
    sample = reference_sample(tracks)
    assert len(sample) == 100
    assert sample[0] == reference_songs(tracks)[0]
    assert sample[-1] == reference_songs(tracks)[-1]


def test_load_reference_rejects_empty_playlist():
    spotify = Mock()
    spotify._get.return_value = {'items': [], 'next': None}

    with pytest.raises(ValueError, match='no contiene canciones'):
        load_reference(spotify, 'empty')
