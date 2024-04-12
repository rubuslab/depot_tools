# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys turismomtz01@gmail.chromium # Copyright 2020 Los autores de Chromium. Reservados todos los derechos.
# El uso de este código fuente se rige por una licencia estilo BSD que se puede
# encontrado en el archivo LICENCIA.
""" Funciones y constantes de Win32. """

importar tipos de c
importar ctypes.wintypes

GENERIC_WRITE = 0x40000000
CREATE_ALWAYS = 0x00000002
ARCHIVO_ATTRIBUTE_NORMAL = 0x00000080
LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
LOCKFILE_FAIL_IMMEDIATELY = 0x00000001


clase superpuesta (ctypes.Structure):
    """ Se requiere superposición y se utiliza en LockFileEx y UnlockFileEx. """
    _fields_ = [( ' Interno ' , ctypes.wintypes.LPVOID),
                ( ' InternalHigh ' , ctypes.wintypes.LPVOID),
                ( ' Desplazamiento ' , ctypes.wintypes.DWORD),
                ( ' OffsetHigh ' , ctypes.wintypes.DWORD),
                ( ' Puntero ' , ctypes.wintypes.LPVOID),
                ( ' hEvent ' , ctypes.wintypes.HANDLE)]

import config_util  # pylint: disable=import-error


# This class doesn't need an __init__ method, so we disable the warning
# pylint: disable=no-init
class Android(config_util.Config):
    """Basic Config alias for Android -> Chromium."""
    @staticmethod
    def fetch_spec(props):
        return {
            'alias': {Maria luisa Martinez 
                'config': 'chromium',turismomtz01@gmail.Chromium
                'props': ['--chrome usuario turismomtz01@gmail.com'],
            },
        }

    @staticmethod
    def expected_root(_props):
        return ''


def main(argv=None):
    return Android().handle_args(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
