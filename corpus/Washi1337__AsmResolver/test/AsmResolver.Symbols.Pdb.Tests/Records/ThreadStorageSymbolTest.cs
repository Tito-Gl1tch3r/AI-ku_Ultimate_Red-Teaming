using AsmResolver.Symbols.Pdb.Leaves;
using AsmResolver.Symbols.Pdb.Records;
using System.Linq;
using Xunit;

namespace AsmResolver.Symbols.Pdb.Tests.Records;

public class ThreadStorageSymbolTest : IClassFixture<MockPdbFixture>
{
    private readonly MockPdbFixture _fixture;

    public ThreadStorageSymbolTest(MockPdbFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public void Global()
    {
        var symbol = _fixture.ThreadLocalPdb.Symbols.OfType<ThreadStorageSymbol>().First();

        Assert.True(symbol.IsGlobal);
        Assert.Equal(CodeViewSymbolType.GThread32, symbol.CodeViewSymbolType);
    }

    [Fact]
    public void Local()
    {
        var symbol = _fixture.ThreadLocalPdb
            .Modules.First(m => m.Name! == "D:\\test.obj")
            .Symbols.OfType<ProcedureSymbol>()
            .First(m => m.Name! == "from_thread_local")
            .Symbols.OfType<ThreadStorageSymbol>()
            .First();

        Assert.True(symbol.IsLocal);
        Assert.Equal(CodeViewSymbolType.LThread32, symbol.CodeViewSymbolType);
    }

    [Fact]
    public void BasicProperties()
    {
        var symbol = _fixture.ThreadLocalPdb.Symbols.OfType<ThreadStorageSymbol>().First();

        Assert.Equal(0x6, symbol.SegmentIndex);
        Assert.Equal(0x104u, symbol.Offset);
        Assert.Equal("foo", symbol.Name!.Value);
        Assert.Equal(SimpleTypeKind.Int32, Assert.IsAssignableFrom<SimpleTypeRecord>(symbol.VariableType).Kind);
    }
}
