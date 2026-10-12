using System.Collections.Generic;
using AsmResolver.IO;

namespace AsmResolver.PE.Relocations.Builder
{
    /// <summary>
    /// Represents one block of relocations to be applied when the PE is loaded into memory.
    /// </summary>
    public sealed class RelocationBlock : SegmentBase
    {
        /// <summary>
        /// Creates a new base relocation block for the provided page.
        /// </summary>
        /// <param name="pageRva">The virtual address of the page to apply base relocations on.</param>
        public RelocationBlock(uint pageRva)
        {
            PageRva = pageRva;
            Entries =  new List<RelocationEntry>();
        }

        /// <summary>
        /// Gets or sets the base RVA for this page.
        /// </summary>
        public uint PageRva
        {
            get;
        }

        /// <summary>
        /// Gets the list of entries added to this page.
        /// </summary>
        public IList<RelocationEntry> Entries
        {
            get;
        }

        /// <inheritdoc />
        public override uint GetPhysicalSize()
        {
            // Align item count to even number (blocks are 32-bit aligned).
            uint totalCount = ((uint) Entries.Count).Align(2);
            return totalCount * sizeof(ushort) + 2 * sizeof(uint);
        }

        /// <inheritdoc />
        public override void Write(BinaryStreamWriter writer)
        {
            // Block header.
            writer.WriteUInt32(PageRva);
            writer.WriteUInt32(GetPhysicalSize());

            // Write all entries in block.
            for (int i = 0; i < Entries.Count; i++)
                Entries[i].Write(writer);

            // Ensure block ends on aligned 32-bit address.
            if (Entries.Count % 2 == 1)
                default(RelocationEntry).Write(writer);
        }

    }
}
