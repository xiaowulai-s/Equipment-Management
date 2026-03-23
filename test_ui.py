#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
OUTPUT_FILE = SCRIPT_DIR / "test_result.txt"

def log(msg):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
    print(msg)

log("=" * 60)
log("Testing PySide6 QML Loading")
log("=" * 60)

try:
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickView

    app = QGuiApplication(sys.argv)

    qml_dir = SCRIPT_DIR / "qml"
    main_qml = qml_dir / "MainView.qml"

    log(f"QML Directory: {qml_dir}")
    log(f"Main QML: {main_qml}")
    log(f"Main QML exists: {main_qml.exists()}")

    # List QML files
    log("\nQML files found:")
    for f in sorted(qml_dir.rglob("*.qml")):
        log(f"  {f.relative_to(SCRIPT_DIR)}")

    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(main_qml.absolute())))

    log(f"View status: {view.status()}")

    if view.status() == 2:
        log("QML loaded successfully!")
        view.show()
        result = app.exec()
        sys.exit(result)
    else:
        log(f"ERROR: status={view.status()}")
        for error in view.errors():
            log(f"Error: {error.toString()}")
        sys.exit(1)

except Exception as e:
    log(f"Exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)