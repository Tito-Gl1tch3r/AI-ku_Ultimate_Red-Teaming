using ZoneTree.AbstractFileStream;
using ZoneTree.Hashers;
using ZoneTree.PresetTypes;

namespace ZoneTree.UnitTests;

public sealed class KeyHasherTests
{
  [Test]
  public void ProvidesHashersForKnownKeyTypes()
  {
    Assert.Multiple(() =>
    {
      Assert.That(ComponentsForKnownTypes.GetKeyHasher<int>(), Is.Not.Null);
      Assert.That(ComponentsForKnownTypes.GetKeyHasher<long>(), Is.Not.Null);
      Assert.That(ComponentsForKnownTypes.GetKeyHasher<Guid>(), Is.Not.Null);
      Assert.That(ComponentsForKnownTypes.GetKeyHasher<string>(), Is.Not.Null);
      Assert.That(
          ComponentsForKnownTypes.GetKeyHasher<Memory<byte>>(),
          Is.Not.Null);
    });
  }

  [Test]
  public void ByteArrayHasherUsesSequenceContent()
  {
    var hasher = new ByteArrayKeyHasher();
    Memory<byte> first = new byte[] { 1, 2, 3, 4 };
    Memory<byte> second = new byte[] { 1, 2, 3, 4 };

    Assert.That(
        hasher.GetHashCode(in first),
        Is.EqualTo(hasher.GetHashCode(in second)));
  }

  [Test]
  public void FactoryPreservesConfiguredKeyHasher()
  {
    var keyHasher = new ConstantKeyHasher();
    var factory = new ZoneTreeFactory<int, int>(
        new InMemoryFileStreamProvider())
        .SetKeyHasher(keyHasher);

    using var zoneTree = factory.OpenOrCreate();

    Assert.That(factory.Options.KeyHasher, Is.SameAs(keyHasher));
  }

  [Test]
  public void FactoryFillsKeyHasherForKnownType()
  {
    var factory = new ZoneTreeFactory<int, int>(
        new InMemoryFileStreamProvider());

    using var zoneTree = factory.OpenOrCreate();

    Assert.That(factory.Options.KeyHasher, Is.TypeOf<DefaultKeyHasher<int>>());
  }

  sealed class ConstantKeyHasher : IKeyHasher<int>
  {
    public int GetHashCode(in int key) => 42;
  }
}
