using DeepEqual.Syntax;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Net.Leksi.Dto;
using NUnit.Framework;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text.Json;
using DtoTestProject.Dto1;

namespace DtoTestProject;

public class DtoJsonConverterUnitTest
{
    private IHost host;

    [OneTimeSetUp]
    public void OneTimeSetup()
    {
        Trace.Listeners.Add(new ConsoleTraceListener());
        IHostBuilder hostBuilder = Host.CreateDefaultBuilder()
            .ConfigureServices(serviceCollection =>
            {
                serviceCollection.AddDtoKit(services =>
                {
                    services.AddTransient<IShipCall, ShipCall>();
                    services.AddTransient<ILocation, Location>();
                    services.AddTransient<IRoute, Route>();
                    services.AddTransient<ILine, Line>();
                    services.AddTransient<IVessel, Vessel>();
                    services.AddTransient<IShipCallForListing, ShipCall>();
                    services.AddTransient<IShipCallAdditionalInfo, ShipCall>();
                    services.AddTransient<IRouteShort, Route>();
                    services.AddTransient<IVesselShort, Vessel>();
                });
            });
        host = hostBuilder.Build();
    }

    [OneTimeTearDown]
    public void OneTimeTearDown()
    {
        Trace.Flush();
    }

    [SetUp]
    public void Setup()
    {
        host.RunAsync();
    }

    [Test]
    public void Test1()
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        dtoBuilder.ValueRequest += args =>
        {
            //Trace.WriteLine(args.Path);
            if(args.IsLeaf)
            {
                args.IsCommited = true;
            }
        };

        IShipCall shipCall = dtoBuilder.Build<IShipCall>();

        DtoJsonConverterFactory converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = true;
        converter.KeysProcessing = KeysProcessing.Usual;
        JsonSerializerOptions options = new() {WriteIndented = true };
        options.Converters.Add(converter);

        string json = JsonSerializer.Serialize(shipCall, options);

        Console.WriteLine(json);

        converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = true;
        converter.KeysProcessing = KeysProcessing.OnlyKeys;
        options = new() { WriteIndented = true };
        options.Converters.Add(converter);
        json = JsonSerializer.Serialize(shipCall, options);

        Console.WriteLine(json);
    }

    [Test]
    [TestCase(true, true)]
    [TestCase(true, false)]
    [TestCase(false, true)]
    [TestCase(false, false)]
    public void Test3(bool withMagic, bool withKeyOnly)
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        int i = 1;

        dtoBuilder.ValueRequest += args =>
        {
            switch (args.Path)
            {
                case "/ID_LINE":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/ID_ROUTE":
                    args.Value = i;
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/ID_LINE":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/ID_RHEAD":
                    args.Value = 1;
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Line/ID_LINE":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Line/Name":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Vessel/ID_VESSEL":
                    args.Value = "VARYAG";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Vessel/Name":
                    args.Value = "VARYAG";
                    args.IsCommited = true;
                    break;
                case "/Voyage":
                    args.Value = "VAR22001";
                    args.IsCommited = true;
                    break;
                case "/VoyageAlt":
                    args.IsCommited = true;
                    break;
                case "/Location/ID_LOCATION":
                    args.Value = i.ToString();
                    args.IsCommited = true;
                    break;
                case "/Location/Type":
                    args.Value = LocationType.Port;
                    args.IsCommited = true;
                    break;
                case "/Location/Unlocode":
                    args.IsCommited = true;
                    break;
                case "/Location/Name":
                    args.IsCommited = true;
                    break;
                case "/ScheduledArrival":
                    args.IsCommited = true;
                    break;
                case "/ActualArrival":
                    args.IsCommited = true;
                    break;
                case "/ScheduledDeparture":
                    args.IsCommited = true;
                    break;
                case "/ActualDeparture":
                    args.IsCommited = true;
                    break;
                case "/Condition":
                    args.IsCommited = true;
                    break;
                case "/AdditionalInfo":
                    args.IsCommited = true;
                    break;
            }
        };

        List<IShipCallForListing> shipCalls = new();

        for(; i <= 3; i++)
        {
            shipCalls.Add(dtoBuilder.Build<IShipCallForListing>());
        }

        DtoJsonConverterFactory converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = withMagic;
        converter.KeysProcessing = withKeyOnly ? KeysProcessing.OnlyKeysForRepeats : KeysProcessing.Usual;
        var options = new JsonSerializerOptions { WriteIndented = true };
        options.Converters.Add(converter);

        string json = JsonSerializer.Serialize(shipCalls, options);

        Console.WriteLine(json);

        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();

        options = new JsonSerializerOptions();
        options.Converters.Add(converter);

        var res = new List<IShipCallForListing>();
        converter.Target = res;
        JsonSerializer.Deserialize<RewritableListStub<IShipCallForListing>>(json, options);

        shipCalls.ShouldDeepEqual(res);

        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = withMagic;
        converter.KeysProcessing = withKeyOnly ? KeysProcessing.OnlyKeysForRepeats : KeysProcessing.Usual;

        options = new JsonSerializerOptions { WriteIndented = true };
        options.Converters.Add(converter);

        Assert.That(JsonSerializer.Serialize<object>(res, options), Is.EqualTo(json));

        foreach(object shipCall in shipCalls)
        {
            ((ShipCall)shipCall).AdditionalInfo = "Additional info";
        }

        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = withMagic;
        converter.KeysProcessing = withKeyOnly ? KeysProcessing.OnlyKeysForRepeats : KeysProcessing.Usual;

        options = new JsonSerializerOptions { WriteIndented = true };
        options.Converters.Add(converter);

        json = JsonSerializer.Serialize(shipCalls.Select(v => (IShipCallAdditionalInfo)v), options);
        Console.WriteLine(json);

        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();

        options = new JsonSerializerOptions();
        options.Converters.Add(converter);

        converter.Target = res;
        JsonSerializer.Deserialize<UpdateableListStub<IShipCallAdditionalInfo>>(json, options);


        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = withMagic;
        converter.KeysProcessing = withKeyOnly ? KeysProcessing.OnlyKeysForRepeats : KeysProcessing.Usual;

        options = new JsonSerializerOptions { WriteIndented = true };
        options.Converters.Add(converter);

        json = JsonSerializer.Serialize(res, options);

        Console.WriteLine(json);

        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = withMagic;
        converter.KeysProcessing = KeysProcessing.OnlyKeys;
        options = new JsonSerializerOptions { WriteIndented = true };
        options.Converters.Add(converter);
        json = JsonSerializer.Serialize(res, options);

        Console.WriteLine(json);

        converter = converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();

        options = new JsonSerializerOptions();
        options.Converters.Add(converter);

        res.Clear();
        converter.Target = res;
        JsonSerializer.Deserialize<RewritableListStub<IShipCallForListing>>(json, options);

        foreach(IShipCallForListing item in res)
        {
            Console.WriteLine(item);
        }

    }

    [Test]
    public void TestEnumAndDateTime()
    {
        ShipCallCondition scc = ShipCallCondition.Booking;
        DateTime dt = DateTime.Now;

        var couple = new { dt, scc };

        DtoJsonConverterFactory converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        converter.WithMagic = true;
        var options = new JsonSerializerOptions { WriteIndented = true };
        options.Converters.Add(converter);

        string json = JsonSerializer.Serialize(couple, options);

        Console.WriteLine(json);

    }

}
