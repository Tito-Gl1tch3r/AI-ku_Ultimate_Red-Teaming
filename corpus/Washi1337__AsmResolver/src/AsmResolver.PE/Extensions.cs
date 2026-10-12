using System.Collections.Generic;
using AsmResolver.Collections;
using AsmResolver.PE.Relocations;

namespace AsmResolver.PE;

internal static class Extensions
{
    public static uint GetFlags(this uint self, int index, uint mask) => (self & mask) >> index;

    public static uint SetFlags(this uint self, int index, uint mask, uint value) => (self & ~mask) | ((value << index) & mask);

    public static IEnumerable<BaseRelocation> CreateBaseRelocations(this ReferenceTable self)
    {
        (int pointerSize, var type) = self.Is32BitTable
            ? (sizeof(uint), RelocationType.HighLow)
            : (sizeof(ulong), RelocationType.Dir64);

        for (int i = 0; i < self.Count; i++)
            yield return new BaseRelocation(type, self.ToReference(i * pointerSize));
    }
}
