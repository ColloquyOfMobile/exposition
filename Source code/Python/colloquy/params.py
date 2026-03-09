import json
from pathlib import Path

DEFAULTS={
    "near_origin_threashold": 400,
    'emulate light sensor': False,
    "arduino": {
        "baudrate": 57600,
        "communication port": None,
            },
    "female1": {
        "dxl origin": 0,
        },
    "female2": {
        "dxl origin": 0,
        },
    "female3": {
        "dxl origin": 0,
        },
    "bar": {
        "dxl origin": 0,
        "interaction_origins": {
          "male1": {
            "female1": 0,
            "female2": 2200,
            "female3": 4300
          },
          "male2": {
            "female1": 6200,
            "female2": 8400,
            "female3": 10400
          }
        }
    },
    "male1": {
        "dxl origin": 0
      },
    "male2": {
        "dxl origin": 0
      }
    }

class Params(dict):
    def __init__(self, path: Path, initial=None, _root=None):
        super().__init__()
        self._path = path
        self._root = _root or self

        if initial:
            for k, v in initial.items():
                self[k] = v

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, Params):
            value = Params(self._path, value, _root=self._root)

        super().__setitem__(key, value)
        self._root._save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._root._save()

    def _save(self):
        if self is not self._root:
            return
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self):
        result = {}
        for k, v in self.items():
            if isinstance(v, Params):
                result[k] = v.to_dict()
            else:
                result[k] = v
        return result

    @classmethod
    def load(cls, path: Path):
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = DEFAULTS
        return cls(path, data)