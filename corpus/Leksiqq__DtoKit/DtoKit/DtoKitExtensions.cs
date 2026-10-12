using Microsoft.Extensions.DependencyInjection;

namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Оболочка для инсталляции в проекте средство для загрузки и сериализации/десериализации DTO.
/// Скрывает детали реализации интерфейсов для работы с DTO от модели, позволяя
/// получать билдер и фабрику конвертеров JSON через механизм внедрения зависимостей
/// </para>
/// <para xml:lang="en">
/// A wrapper to install in a project the means to load and serialize/deserialize DTOs.
/// Hides the implementation details of DTO interfaces from the model, allowing
/// get JSON converter builder and factory via DI
/// </para>
/// </summary>
public static class DtoKitExtensions
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Инсталлирует в проекте средство для загрузки и сериализации/десериализации DTO.
    /// </para>
    /// <para xml:lang="en">
    /// Installs a facility in the project to load and serialize/deserialize DTOs.
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
    /// <see cref="Action{IServiceCollection}"/> для непосредственного выполнения регистрации
    /// </para>
    /// <para xml:lang="en">
    /// <see cref="Action{IServiceCollection}"/> to perform registration itself
    /// </para>
    /// </param>
    /// <example>
    /// <code>
    /// IHostBuilder hostBuilder = Host.CreateDefaultBuilder()
    ///.AddDtoKit(services =>
    /// {
    ///     services.AddTransient&lt;IShipCall, ShipCall&gt;();
    ///     services.AddTransient&lt;ILocation, Location&gt;();
    ///     services.AddTransient&lt;IRoute, Route&gt;();
    ///     services.AddTransient&lt;ILine, Line&gt;();
    ///     services.AddTransient&lt;IVessel, Vessel&gt;();
    ///     services.AddTransient&lt;IShipCallForListing, ShipCall&gt;();
    ///     services.AddTransient&lt;IShipCallAdditionalInfo, ShipCall&gt;();
    ///     services.AddTransient&lt;IArrivalShipCall, ShipCall&gt;();
    ///     services.AddTransient&lt;IDepartureShipCall, ShipCall&gt;();
    ///     services.AddTransient&lt;IRouteShort, Route&gt;();
    ///     services.AddTransient&lt;IVesselShort, Vessel&gt;();
    ///     services.AddTransient&lt;ITravelForListing, Travel&gt;();
    ///});
    ///host = hostBuilder.Build();
    /// </code>
    /// </example>
    public static IServiceCollection AddDtoKit(this IServiceCollection services, Action<IServiceCollection> configure)
    {
        services.AddDtoCore(configure);
        services.AddSingleton(opt => new TypesForest(opt.GetRequiredService<DtoServiceProvider>()));
        services.AddTransient(opt => new DtoBuilder(opt.GetRequiredService<TypesForest>()));
        services.AddTransient(opt => new DtoJsonConverterFactory(opt.GetRequiredService<TypesForest>()));
        return services;
    }
}
