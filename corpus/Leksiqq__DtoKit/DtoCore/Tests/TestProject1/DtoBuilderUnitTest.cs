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

public class DtoBuilderUnitTest
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
                    services.AddTransient<IShipCallKey, ShipCallKey>();
                    services.AddTransient<ILocation, Location>();
                    services.AddTransient<IRoute, Route>();
                    services.AddTransient<ILine, Line>();
                    services.AddTransient<ILineKey, LineKey>();
                    services.AddTransient<IVessel, Vessel>();
                    services.AddTransient<IShipCallForListing, ShipCall>();
                    services.AddTransient<IShipCallAdditionalInfo, ShipCall>();
                    services.AddTransient<IArrivalShipCall, ShipCall>();
                    services.AddTransient<IDepartureShipCall, ShipCall>();
                    services.AddTransient<IRouteShort, Route>();
                    services.AddTransient<IVesselShort, Vessel>();
                    services.AddTransient<ITravelForListing, Travel>();
                });
            });
        host = hostBuilder.Build();
    }

    [OneTimeTearDown]
    public void OneTimeTearDown()
    {
        Trace.Flush();
    }

    [NUnit.Framework.SetUp]
    public void Setup()
    {
        host.RunAsync();
    }

    [Test]
    public void TestComplexKey() 
    {
        TypesForest tf = host.Services.GetRequiredService<TypesForest>();

        TypeNode typeNode = tf.GetTypeNode(typeof(ILine));
        object[]? objects = typeNode.GetKey(new Line { ID = new LineKey { ID_LINE = "NTL" }, Name = "NTL" });
        //Console.WriteLine(string.Join("\n", tf.GetTypeNode(typeof(ILine)).ValueRequests));
        Console.WriteLine(string.Join("\n", objects));
    }

    [Test]
    public void Test1()
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        int tabPos = 35;

        dtoBuilder.ValueRequest += args =>
        {
            string kind = (args.IsNullable ? "nullable" : "not nullable") + " " + (args.IsLeaf ? "leaf" : "node");
            Trace.WriteLine($"{args.Path}{string.Join("", Enumerable.Range(0, tabPos - args.Path.Length).Select(v => " "))}({kind})");
            if (args.IsLeaf)
            {
                args.IsCommited = true;
            }
        };

        IShipCall shipCall = dtoBuilder.Build<IShipCall>();

    }

    [Test]
    public void Test2()
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        Trace.WriteLine(dtoBuilder.GenerateHandlerSkeleton<IShipCall>());
    }

    [Test]
    public void Test3()
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        int i = 1;

        dtoBuilder.ValueRequest += args =>
        {
            switch (args.Path)
            {
                case "/ID/ID_LINE":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/ID/ID_ROUTE":
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
                case "/RouteImpl/Line/ID/ID_LINE":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Line/ShortName":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Line/Name":
                    args.Value = "TRE";
                    args.IsCommited = true;
                    break;
                case "/RouteImpl/Vessel":
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
                case "/Location":
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
    }

    [Test]
    public void Test4()
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        Trace.WriteLine(dtoBuilder.GenerateHandlerSkeleton<IVessel>());
    }


    internal class Helper1
    {

        [Path("/")]
        object Apache(string path, Type type, object value, ref bool isCommited)
        {
            //isCommited = true;
            return new Line { ID = new LineKey { ID_LINE = "NTL" }, Name = "NTL" };
        }

        [Path("/ID/ID_LINE")]
        [Path("/Name")]
        [Path("/ShortName")]
        object Netscape(string path, Type type, object value, ref bool isCommited)
        {
            return "TRE";
        }

        [Setup]
        void Setup()
        {
            Trace.WriteLine("Setup");
        }
        [Shutdown]
        void Shutdown()
        {
            Trace.WriteLine("Shutdown");
        }
    }

    [Test]
    public void Test5()
    {
        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();
        DtoJsonConverterFactory converter = host.Services.GetRequiredService<DtoJsonConverterFactory>();
        JsonSerializerOptions options = new JsonSerializerOptions { };
        options.Converters.Add(converter);

        ILine line = dtoBuilder.Build<ILine>(new Helper1());

        //Trace.WriteLine(line.Name);

        Trace.WriteLine(JsonSerializer.Serialize(line, options));

    }

    [Test]
    public void Test6()
    {

        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        Trace.WriteLine(dtoBuilder.GenerateHandlerSkeleton<IShipCallForListing>());
    }

    [Test]
    public void Test7()
    {

        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        Trace.WriteLine(dtoBuilder.GenerateHelperSkeleton<ITravelForListing>());
    }

    class TravelHelper
    {
        [Path("/ArrivalShipCall")]
        public object Set_ArrivalShipCall(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            return null;
        }

        [Path("/ArrivalShipCall/ID_LINE")]
        public object Set_ArrivalShipCall_ID_LINE(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/ID_ROUTE")]
        public object Set_ArrivalShipCall_ID_ROUTE(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/ActualArrival")]
        public object Set_ArrivalShipCall_ActualArrival(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/Location")]
        public object Set_ArrivalShipCall_Location(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/Location/ID_LOCATION")]
        public object Set_ArrivalShipCall_Location_ID_LOCATION(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/Location/Name")]
        public object Set_ArrivalShipCall_Location_Name(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/Location/Type")]
        public object Set_ArrivalShipCall_Location_Type(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/ArrivalShipCall/Location/Unlocode")]
        public object Set_ArrivalShipCall_Location_Unlocode(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/DepartureShipCall")]
        public object Set_DepartureShipCall(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/DepartureShipCall/ID_LINE")]
        public object Set_DepartureShipCall_ID_LINE(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

        [Path("/DepartureShipCall/ID_ROUTE")]
        public object Set_DepartureShipCall_ID_ROUTE(string path, Type type, object value, bool isNullable, ref bool isCommited)
        {
            throw new NotImplementedException();
        }

    }

    [Test]
    public void Test8()
    {

        DtoBuilder dtoBuilder = host.Services.GetRequiredService<DtoBuilder>();

        dtoBuilder.Build<ITravelForListing>(new TravelHelper());
    }

}
