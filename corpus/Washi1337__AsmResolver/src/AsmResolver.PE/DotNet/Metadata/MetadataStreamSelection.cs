namespace AsmResolver.PE.DotNet.Metadata;

/// <summary>
/// Represents a selection of metadata streams from a <see cref="MetadataDirectory"/>.
/// </summary>
public struct MetadataStreamSelection
{
    /// <summary>
    /// Gets the main tables stream in the metadata directory.
    /// </summary>
    public TablesStream? TablesStream { get; set; }

    /// <summary>
    /// Gets the original index of the tables stream.
    /// </summary>
    public int TablesStreamIndex { get; set; }

    /// <summary>
    /// Gets the main blob stream in the metadata directory.
    /// </summary>
    public BlobStream? BlobStream { get; set; }

    /// <summary>
    /// Gets the original index of the blob stream.
    /// </summary>
    public int BlobStreamIndex { get; set; }

    /// <summary>
    /// Gets the main GUID stream in the metadata directory.
    /// </summary>
    public GuidStream? GuidStream { get; set; }

    /// <summary>
    /// Gets the original index of the GUID stream.
    /// </summary>
    public int GuidStreamIndex { get; set; }

    /// <summary>
    /// Gets the main strings stream in the metadata directory.
    /// </summary>
    public StringsStream? StringsStream { get; set; }

    /// <summary>
    /// Gets the original index of the strings stream.
    /// </summary>
    public int StringsStreamIndex { get; set; }

    /// <summary>
    /// Gets the main user-strings stream in the metadata directory.
    /// </summary>
    public UserStringsStream? UserStringsStream { get; set; }

    /// <summary>
    /// Gets the original index of the user-strings stream.
    /// </summary>
    public int UserStringsStreamIndex { get; set; }
}
