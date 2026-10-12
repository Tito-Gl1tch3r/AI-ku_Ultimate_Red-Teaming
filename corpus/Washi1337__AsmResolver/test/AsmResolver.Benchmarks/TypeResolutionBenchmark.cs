using AsmResolver.DotNet;
using AsmResolver.DotNet.Serialized;
using AsmResolver.DotNet.TestCases.Methods;
using AsmResolver.DotNet.TestCases.Types;
using AsmResolver.IO;
using BenchmarkDotNet.Attributes;

namespace AsmResolver.Benchmarks;

[MemoryDiagnoser]
public class TypeResolutionBenchmark
{
    [Params(false, true)]
    public bool UsingRuntimeContext { get; set; }

    [Benchmark]
    public void ResolveSystemObjectInTwoAssemblies()
    {
        var service = new ByteArrayFileService();
        var parameters = new ModuleReaderParameters(service);

        var module1 = ModuleDefinition.FromFile(typeof(Class).Assembly.Location, readerParameters: parameters);
        var module2 = (UsingRuntimeContext
                ? module1.RuntimeContext!.LoadAssembly(typeof(SingleMethod).Assembly.Location)
                : AssemblyDefinition.FromFile(typeof(SingleMethod).Assembly.Location, readerParameters: parameters))
            .ManifestModule!;

        _ = module1.CorLibTypeFactory.Object.Resolve(module1.RuntimeContext);
        _ = module2.CorLibTypeFactory.Object.Resolve(module1.RuntimeContext);
    }
}
