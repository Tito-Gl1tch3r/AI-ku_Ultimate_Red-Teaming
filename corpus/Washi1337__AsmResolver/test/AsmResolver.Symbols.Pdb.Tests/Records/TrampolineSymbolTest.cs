using AsmResolver.Symbols.Pdb.Records;
using System.Collections.Generic;
using System.Linq;
using Xunit;

namespace AsmResolver.Symbols.Pdb.Tests.Records;

public class TrampolineSymbolTest : IClassFixture<MockPdbFixture>
{
    private readonly PdbModule _module;

    public TrampolineSymbolTest(MockPdbFixture fixture)
    {
        _module = fixture.TrampolinePdb.Modules.First(x => x.Name == "* Linker *");
    }

    [Fact]
    public void Properties()
    {
        IEnumerable<(TrampolineSymbolKind, uint, uint, uint, uint, uint)> actual =
            _module.Symbols.OfType<TrampolineSymbol>()
            .Select(x =>
                (x.Kind,
                (uint)x.TargetSegmentIndex,
                x.TargetOffset,
                (uint)x.ThunkSegmentIndex,
                x.ThunkOffset,
                (uint)x.ThunkSize));

        Assert.Equal(new[]
        {
            (TrampolineSymbolKind.Incremental, 0x1u, 0x30u, 0x1u, 0x5u, 0x5u),
            (TrampolineSymbolKind.Incremental, 0x1u, 0x40u, 0x1u, 0xau, 0x5u),
            (TrampolineSymbolKind.Incremental, 0x1u, 0x90u, 0x1u, 0xfu, 0x5u),
            (TrampolineSymbolKind.Incremental, 0x1u, 0xb0u, 0x1u, 0x14u, 0x5u),
        }, actual);
    }
}
