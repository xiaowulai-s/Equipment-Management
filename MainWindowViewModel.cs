using Prism.Mvvm;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Windows.Threading;

namespace EquipmentManagement;

public class MainWindowViewModel : BindableBase
{
    // 标题
    private string _title = "Pump Station A";
    public string Title
    {
        get => _title;
        set => SetProperty(ref _title, value);
    }

    // 设备列表
    private ObservableCollection<DeviceItem> _devices;
    public ObservableCollection<DeviceItem> Devices
    {
        get => _devices;
        set => SetProperty(ref _devices, value);
    }

    // 当前选中的设备
    private DeviceItem _selectedDevice;
    public DeviceItem SelectedDevice
    {
        get => _selectedDevice;
        set => SetProperty(ref _selectedDevice, value);
    }

    // 定时器用于模拟实时数据更新
    private DispatcherTimer _dataUpdateTimer;



    // 仪表盘数据
    public ObservableCollection<GaugeData> Gauges {
        get;
        set;
    }

    // 数据卡片
    public ObservableCollection<DataCard> DataCards {
        get;
        set;
    }

    // Modbus寄存器数据
    public ObservableCollection<RegisterItem> Registers {
        get;
        set;
    }

    public MainWindowViewModel()
    {
        InitializeData();
        InitializeTimer();
    }

    private void InitializeData()
    {
        // 初始化设备列表
        Devices = new ObservableCollection<DeviceItem>
        {
            new DeviceItem { Id = 1, Name = "Sensor Node B", Icon = "📡" },
            new DeviceItem { Id = 2, Name = "Sensor Node T", Icon = "📡" },
            new DeviceItem { Id = 3, Name = "Sensor Node A", Icon = "📡" },
            new DeviceItem { Id = 4, Name = "Mirmor Node L", Icon = "🔄" },
            new DeviceItem { Id = 5, Name = "LwllmpNode S", Icon = "🔄" },
            new DeviceItem { Id = 6, Name = "Fansoh Loss", Icon = "⚠️" }
        };

        // 设置默认选中设备
        SelectedDevice = Devices[0];

        // 初始化仪表盘数据
        InitializeGaugeData();

        // 初始化数据卡片
        InitializeDataCards();

        // 初始化寄存器数据
        InitializeRegisterData();
    }



    private void InitializeGaugeData()
    {
        Gauges = new ObservableCollection<GaugeData>
        {
            new GaugeData { Name = "SQ10", Value = 75.5, Min = 0, Max = 100, Color = "#00FFAA" },
            new GaugeData { Name = "AR2", Value = 115.2, Min = 0, Max = 220, Color = "#00AAFF" },
            new GaugeData { Name = "B", Value = 12.8, Min = 0, Max = 20, Color = "#FFAA00" },
            new GaugeData { Name = "", Value = 14.8, Min = 0, Max = 25, Color = "#AA00FF" }
        };
    }

    private void InitializeDataCards()
    {
        DataCards = new ObservableCollection<DataCard>
        {
            new DataCard { Name = "Temperature", Value = "25.5°C", Progress = 65, Unit = "°C", Color = "#00FFAA" },
            new DataCard { Name = "Pressure", Value = "123 AsB", Progress = 72, Unit = "AsB", Color = "#00AAFF" },
            new DataCard { Name = "Gas Concentration", Value = "405 cAsB (123°C)", Progress = 45, Unit = "cAsB", Color = "#FFAA00" }
        };
    }

    private void InitializeRegisterData()
    {
        Registers = new ObservableCollection<RegisterItem>
        {
            new RegisterItem { Address = "0x0001", Valate = "06", Value = "25.5", Status = "OK", StatusColor = "#00FFAA", StatusText = "OK" },
            new RegisterItem { Address = "0x0001", Valate = "24", Value = "20:25", Status = "OK", StatusColor = "#00FFAA", StatusText = "OK" },
            new RegisterItem { Address = "0x0001", Valate = "1", Value = "10:55", Status = "OK", StatusColor = "#00FFAA", StatusText = "OK" }
        };
    }

    // 初始化定时器
    private void InitializeTimer()
    {
        _dataUpdateTimer = new DispatcherTimer();
        _dataUpdateTimer.Interval = TimeSpan.FromMilliseconds(1000); // 每秒更新一次
        _dataUpdateTimer.Tick += (sender, e) => UpdateRealTimeData();
        _dataUpdateTimer.Start();
    }

    // 更新实时数据
    private void UpdateRealTimeData()
    {
        var random = new Random();
        
        // 更新仪表盘数据
        foreach (var gauge in Gauges)
        {
            double change = (random.NextDouble() * 4) - 2; // -2 到 +2 的随机变化
            gauge.Value = Math.Max(gauge.Min, Math.Min(gauge.Max, gauge.Value + change));
        }

        // 更新数据卡片
        double tempChange = (random.NextDouble() * 2) - 1;
        double temp = double.Parse(DataCards[0].Value.Replace("°C", "")) + tempChange;
        DataCards[0].Value = $"{temp:F1}°C";
        DataCards[0].Progress = (int)Math.Max(0, Math.Min(100, DataCards[0].Progress + (random.NextDouble() * 4) - 2));

        double pressureChange = (random.NextDouble() * 10) - 5;
        int pressure = int.Parse(DataCards[1].Value.Replace(" AsB", "")) + (int)pressureChange;
        DataCards[1].Value = $"{pressure} AsB";
        DataCards[1].Progress = (int)Math.Max(0, Math.Min(100, DataCards[1].Progress + (random.NextDouble() * 4) - 2));

        double gasChange = (random.NextDouble() * 20) - 10;
        int gas = int.Parse(DataCards[2].Value.Split(' ')[0]) + (int)gasChange;
        int gasTemp = 123 + (int)((random.NextDouble() * 4) - 2);
        DataCards[2].Value = $"{gas} cAsB ({gasTemp}°C)";
        DataCards[2].Progress = (int)Math.Max(0, Math.Min(100, DataCards[2].Progress + (random.NextDouble() * 4) - 2));

        // 更新寄存器数据
        double regTemp = double.Parse(Registers[0].Value) + (random.NextDouble() * 1) - 0.5;
        Registers[0].Value = $"{regTemp:F1}";
    }
}

// 设备项模型
public class DeviceItem
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string Icon { get; set; }
}

// 仪表盘数据模型
public class GaugeData : BindableBase
{
    private string _name;
    public string Name
    {
        get => _name;
        set => SetProperty(ref _name, value);
    }

    private double _value;
    public double Value
    {
        get => _value;
        set => SetProperty(ref _value, value);
    }

    private double _min;
    public double Min
    {
        get => _min;
        set => SetProperty(ref _min, value);
    }

    private double _max;
    public double Max
    {
        get => _max;
        set => SetProperty(ref _max, value);
    }

    private string _color;
    public string Color
    {
        get => _color;
        set => SetProperty(ref _color, value);
    }
}

// 数据卡片模型
public class DataCard : BindableBase
{
    private string _name;
    public string Name
    {
        get => _name;
        set => SetProperty(ref _name, value);
    }

    private string _value;
    public string Value
    {
        get => _value;
        set => SetProperty(ref _value, value);
    }

    private int _progress;
    public int Progress
    {
        get => _progress;
        set => SetProperty(ref _progress, value);
    }

    private string _unit;
    public string Unit
    {
        get => _unit;
        set => SetProperty(ref _unit, value);
    }

    private string _color;
    public string Color
    {
        get => _color;
        set => SetProperty(ref _color, value);
    }
}

// 寄存器项模型
public class RegisterItem : BindableBase
{
    private string _address;
    public string Address
    {
        get => _address;
        set => SetProperty(ref _address, value);
    }

    private string _valate;
    public string Valate
    {
        get => _valate;
        set => SetProperty(ref _valate, value);
    }

    private string _value;
    public string Value
    {
        get => _value;
        set => SetProperty(ref _value, value);
    }

    private string _status;
    public string Status
    {
        get => _status;
        set => SetProperty(ref _status, value);
    }

    private string _statusColor;
    public string StatusColor
    {
        get => _statusColor;
        set => SetProperty(ref _statusColor, value);
    }

    private string _statusText;
    public string StatusText
    {
        get => _statusText;
        set => SetProperty(ref _statusText, value);
    }
}