using System.Windows;
using Prism.Ioc;
using Prism.Modularity;

namespace EquipmentManagement;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : PrismApplication
{
    protected override Window CreateShell()
    {
        return Container.Resolve<MainWindow>();
    }

    protected override void RegisterTypes(IContainerRegistry containerRegistry)
    {
        // 注册服务和视图模型
        containerRegistry.RegisterForNavigation<MainWindow>();
        containerRegistry.RegisterSingleton<MainWindowViewModel>();
    }

    protected override void ConfigureModuleCatalog(IModuleCatalog moduleCatalog)
    {
        // 注册模块
        base.ConfigureModuleCatalog(moduleCatalog);
    }
}

