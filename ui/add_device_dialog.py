# -*- coding: utf-8 -*-
"""
Add/Edit Device Wizard Dialog - QWizard Multi-Page Version (v3.2)

Provides 4-step wizard for device configuration:
1. ConnectionPage: Device connection parameters
2. RegisterMapPage: Data point mapping table
3. PollingConfigPage: Polling frequency settings
4. SummaryPage: Configuration preview and confirmation
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from core.device.device_type_manager import DeviceTypeManager
from core.device.device_factory import ProtocolType
from ui.device_type_dialogs import DeviceTypeDialog


class ConnectionPage(QWizardPage):
    """Wizard Page 1: Device Connection Basic Parameters"""
    
    # Signal emited when protocol type changes
    protocolChanged = Signal(ProtocolType)
    
    def __init__(self, device_type_manager: DeviceTypeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.device_type_manager = device_type_manager
        self.setTitle("Connection Configuration")
        self.setSubTitle("Configure device connection parameters")
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize UI components"""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Device name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter device name")
        layout.addRow("Device Name:", self.name_edit)
        
        # Protocol type
        self.protocol_combo = QComboBox()
        for protocol in ProtocolType:
            self.protocol_combo.addItem(protocol.value, protocol)
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        layout.addRow("Protocol:", self.protocol_combo)
        
        # Dynamic parameter area (changes based on protocol type)
        self.param_container = QWidget()
        self.param_layout = QFormLayout(self.param_container)
        layout.addRow(self.param_container)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._on_test_connection)
        layout.addRow("", self.test_btn)
    
    def _on_protocol_changed(self, index: int) -> None:
        """Handle protocol type change"""
        protocol = self.protocol_combo.itemData(index)
        self.protocolChanged.emit(protocol)
        
        # Update dynamic parameters based on protocol
        self._update_dynamic_params(protocol)
    
    def _update_dynamic_params(self, protocol: ProtocolType) -> None:
        """Update dynamic parameters based on protocol type"""
        # Clear existing dynamic parameters
        while self.param_layout.rowCount() > 0:
            self.param_layout.removeRow(0)
        
        if protocol == ProtocolType.MODBUS_TCP:
            # IP address
            self.ip_edit = QLineEdit()
            self.ip_edit.setPlaceholderText("192.168.1.100")
            self.param_layout.addRow("IP Address:", self.ip_edit)
            
            # Port
            self.port_spin = QSpinBox()
            self.port_spin.setRange(1, 65535)
            self.port_spin.setValue(502)
            self.param_layout.addRow("Port:", self.port_spin)
            
        elif protocol == ProtocolType.MODBUS_RTU:
            # Serial port
            self.port_combo = self._build_serial_port_combo()
            self.param_layout.addRow("Serial Port:", self.port_combo)
            
            # Baudrate
            self.baudrate_combo = QComboBox()
            for baud in [9600, 14400, 19200, 38400, 57600, 115200]:
                self.baudrate_combo.addItem(str(baud), baud)
            self.param_layout.addRow("Baudrate:", self.baudrate_combo)
            
            # Data bits, parity, stop bits...
            # (simplified for brevity)
    
    def _build_serial_port_combo(self) -> QComboBox:
        """Build serial port selection combo box"""
        combo = QComboBox()
        # Add available serial ports
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            combo.addItem(f"{port.device} - {port.description}", port.device)
        return combo
    
    def _on_test_connection(self) -> None:
        """Test device connection"""
        QMessageBox.information(
            self,
            "Test Result",
            "Connection test completed (simulated)"
        )
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration"""
        config = {
            "name": self.name_edit.text(),
            "protocol": self.protocol_combo.currentData().value,
        }
        
        protocol = self.protocol_combo.currentData()
        if protocol == ProtocolType.MODBUS_TCP:
            config["ip"] = self.ip_edit.text()
            config["port"] = self.port_spin.value()
        elif protocol == ProtocolType.MODBUS_RTU:
            config["port"] = self.port_combo.currentData()
            config["baudrate"] = self.baudrate_combo.currentData()
        
        return config


class RegisterMapPage(QWizardPage):
    """Wizard Page 2: Data Point Mapping Table"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Data Point Configuration")
        self.setSubTitle("Configure register mapping for data points")
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_row)
        toolbar.addWidget(add_btn)
        
        remove_btn = QPushButton("- Remove")
        remove_btn.clicked.connect(self._remove_row)
        toolbar.addWidget(remove_btn)
        
        toolbar.addStretch()
        
        preset_combo = QComboBox()
        preset_combo.addItem("Load Preset...", "")
        preset_combo.addItem("8-Channel Relay", "relay_8")
        preset_combo.addItem("Temperature Sensor", "temp_sensor")
        preset_combo.currentTextChanged.connect(self._apply_preset)
        toolbar.addWidget(preset_combo)
        
        layout.addLayout(toolbar)
        
        # Data point table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Data Type", "Address", "Writable", "Decimals", "Scale", "Unit"
        ])
        layout.addWidget(self.table)
        
        # Count label
        self.count_label = QLabel("0 data points configured")
        layout.addWidget(self.count_label)
    
    def _add_row(self) -> None:
        """Add a new row to the table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Name
        name_edit = QLineEdit()
        self.table.setCellWidget(row, 0, name_edit)
        
        # Data type combo
        type_combo = QComboBox()
        type_combo.addItem("Input Float32", "input_float32")
        type_combo.addItem("Holding Float32", "holding_float32")
        type_combo.addItem("Input Int16", "input_int16")
        type_combo.addItem("Holding Int16", "holding_int16")
        self.table.setCellWidget(row, 1, type_combo)
        
        # Address spin
        addr_spin = QSpinBox()
        addr_spin.setRange(0, 65535)
        self.table.setCellWidget(row, 2, addr_spin)
        
        # Writable combo
        writable_combo = QComboBox()
        writable_combo.addItem("Read Only", False)
        writable_combo.addItem("Read/Write", True)
        self.table.setCellWidget(row, 3, writable_combo)
        
        # Decimals spin
        decimal_spin = QSpinBox()
        decimal_spin.setRange(0, 4)
        self.table.setCellWidget(row, 4, decimal_spin)
        
        # Scale spin
        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(0.0, 9999.0)
        scale_spin.setValue(1.0)
        self.table.setCellWidget(row, 5, scale_spin)
        
        # Unit edit
        unit_edit = QLineEdit()
        self.table.setCellWidget(row, 6, unit_edit)
        
        self._update_count()
    
    def _remove_row(self) -> None:
        """Remove selected row"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            self._update_count()
    
    def _apply_preset(self, preset_type: str) -> None:
        """Apply preset template"""
        if preset_type == "relay_8":
            # 8-channel relay preset
            for i in range(8):
                self._add_row()
                row = self.table.rowCount() - 1
                name_edit = self.table.cellWidget(row, 0)
                if isinstance(name_edit, QLineEdit):
                    name_edit.setText(f"Relay_{i+1}")
        elif preset_type == "temp_sensor":
            # Temperature sensor preset
            self._add_row()
            row = self.table.rowCount() - 1
            name_edit = self.table.cellWidget(row, 0)
            if isinstance(name_edit, QLineEdit):
                name_edit.setText("Temperature")
    
    def _update_count(self) -> None:
        """Update count label"""
        count = self.table.rowCount()
        self.count_label.setText(f"{count} data points configured")
        self.completeChanged.emit()
    
    def validatePage(self) -> bool:
        """Validate page: at least one data point"""
        if self.table.rowCount() == 0:
            QMessageBox.warning(
                self, "Incomplete Configuration",
                "Please configure at least one data point!"
            )
            return False
        return True
    
    def get_register_points(self) -> List[Dict[str, Any]]:
        """Get register point configuration"""
        points = []
        for row in range(self.table.rowCount()):
            point = {}
            
            name_widget = self.table.cellWidget(row, 0)
            if isinstance(name_widget, QLineEdit):
                point["name"] = name_widget.text()
            
            type_widget = self.table.cellWidget(row, 1)
            if isinstance(type_widget, QComboBox):
                point["data_type"] = type_widget.currentData()
            
            # (simplified for brevity - other fields)
            points.append(point)
        
        return points
    
    def set_register_points(self, points: List[Dict[str, Any]]) -> None:
        """Set data point configuration (edit mode)"""
        self.table.setRowCount(0)
        
        for point_data in points:
            self._add_row()
            # (simplified for brevity - fill in data)


class PollingConfigPage(QWizardPage):
    """Wizard Page 3: Polling Configuration"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Polling Configuration")
        self.setSubTitle("Set data collection frequency and optimization options")
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize UI components"""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Polling interval
        self.polling_interval = QSpinBox()
        self.polling_interval.setRange(100, 60000)
        self.polling_interval.setValue(1000)
        self.polling_interval.setSuffix(" ms")
        layout.addRow("Polling Interval:", self.polling_interval)
        
        # Batch read optimization
        self.batch_read_check = QCheckBox("Enable batch read optimization")
        self.batch_read_check.setChecked(True)
        layout.addRow("", self.batch_read_check)
    
    def get_polling_config(self) -> Dict[str, Any]:
        """Get polling configuration"""
        return {
            "polling_interval_ms": self.polling_interval.value(),
            "batch_optimization": self.batch_read_check.isChecked(),
        }


class SummaryPage(QWizardPage):
    """Wizard Page 4: Configuration Summary and Confirmation"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Configuration Confirmation")
        self.setSubTitle("Please review the configuration information and click 'Finish' to add device")
        self._config_summary: Dict[str, Any] = {}
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Summary text
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(300)
        layout.addWidget(self.summary_text)
    
    def initializePage(self) -> None:
        """Initialize page with configuration summary"""
        # Collect configuration from previous pages
        wizard = self.wizard()
        if hasattr(wizard, 'get_all_config'):
            self._config_summary = wizard.get_all_config()
        
        # Display summary
        summary = "Configuration Summary:\n\n"
        for key, value in self._config_summary.items():
            summary += f"  {key}: {value}\n"
        
        self.summary_text.setText(summary)


class AddDeviceDialog(QWizard):
    """Main wizard dialog for adding/editing devices"""
    
    def __init__(self, device_type_manager: DeviceTypeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.device_type_manager = device_type_manager
        
        self.setWindowTitle("Add/Edit Device")
        self.setWizardStyle(QWizard.WizardStyle.ModermStyle)
        
        # Create pages
        self.connection_page = ConnectionPage(device_type_manager, self)
        self.register_page = RegisterMapPage(self)
        self.polling_page = PollingConfigPage(self)
        self.summary_page = SummaryPage(self)
        
        # Add pages to wizard
        self.addPage(self.connection_page)
        self.addPage(self.register_page)
        self.addPage(self.polling_page)
        self.addPage(self.summary_page)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration from all pages"""
        config = {}
        
        # Connection config
        config["connection"] = self.connection_page.get_connection_config()
        
        # Register config
        config["registers"] = self.register_page.get_register_points()
        
        # Polling config
        config["polling"] = self.polling_page.get_polling_config()
        
        return config
