using Microsoft.Extensions.DependencyInjection;

namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Класс, предоставляющий расширение для <see cref="IServiceCollection"/> предназначенное для 
/// включения инфраструктуры поддержки Dto
/// </para>
/// <para xml:lang="en">
/// A class that provides an extension to <see cref="IServiceCollection"/> for
/// enabling Dto support infrastructure
/// </para>
/// </summary>
public static class DtoCoreExtensions
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Даёт возможность совместить регистрацию итерфейсов с их регистрацией в DI
    /// </para>
    /// <para xml:lang="en">
    /// Makes it possible to combine the registration of interfaces with their registration in DI
    /// </para>
    /// </summary>
    /// <param name="services">
    /// <para xml:lang="ru">
    /// Коллекция сервисов, предоставляемая хостом для конфигурации DI
    /// </para>
    /// <para xml:lang="en">
    /// Collection of services provided by host for DI configuration
    /// </para>
    /// </param>
    /// <param name="configure">
    /// <para xml:lang="ru">
    /// <see cref="Action{IServiceCollection}"/> для непосредственного выполненя регистрации
    /// </para>
    /// <para xml:lang="en">
    /// <see cref="Action{IServiceCollection}"/> to perform registration itself
    /// </para>
    /// </param>
    /// <example>
    /// <code>
    /// IHostBuilder hostBuilder = Host.CreateDefaultBuilder()
    ///.AddDtoCore(services =>
    ///    {
    ///        services.AddTransient&lt;IShipCall, ShipCall&gt;();
    ///        services.AddTransient&lt;ILocation, Location&gt;();
    ///        services.AddTransient&lt;IRoute, Route&gt;();
    ///        services.AddTransient&lt;ILine, Line&gt;();
    ///        services.AddTransient&lt;IVessel, Vessel&gt;();
    ///        services.AddTransient&lt;IShipCallForListing, ShipCall&gt;();
    ///        services.AddTransient&lt;IShipCallAdditionalInfo, ShipCall&gt;();
    ///        services.AddTransient&lt;IArrivalShipCall, ShipCall&gt;();
    ///        services.AddTransient&lt;IDepartureShipCall, ShipCall&gt;();
    ///        services.AddTransient&lt;IRouteShort, Route&gt;();
    ///        services.AddTransient&lt;IVesselShort, Vessel&gt;();
    ///        services.AddTransient&lt;ITravelForListing, Travel&gt;();
    ///    });
    ///host = hostBuilder.Build();
    /// </code>
    /// </example>
    public static IServiceCollection AddDtoCore(this IServiceCollection services, Action<IServiceCollection> configure)
    {
        DtoServiceProvider instance = new(null);
        services.AddSingleton<DtoServiceProvider>(serviceProvider =>
        {
            instance._serviceProvider = serviceProvider;
            return instance;
        });
        instance._services = services;
        configure?.Invoke(instance);
        instance._services = null;
        return services;
    }
}
