"""Reject the reproduced zero-plane green output, even when JPEG decode succeeds."""
import json
from pathlib import Path
import sys
from PIL import Image, ImageStat


def picture_stats(path):
    with Image.open(path) as image:
        sample = image.convert('RGB').resize((400, 400))
    stats = ImageStat.Stat(sample)
    zero_planes = (stats.mean[0] < 3 and stats.mean[2] < 3 and
                   80 < stats.mean[1] < 150 and max(stats.stddev) < 4)
    return {'mean_rgb': stats.mean, 'stddev_rgb': stats.stddev, 'zero_plane_green': zero_planes}


if __name__ == '__main__':
    result = picture_stats(Path(sys.argv[1]))
    print(json.dumps(result))
    assert not result['zero_plane_green'], 'Reproduced GR zero-plane green output'
