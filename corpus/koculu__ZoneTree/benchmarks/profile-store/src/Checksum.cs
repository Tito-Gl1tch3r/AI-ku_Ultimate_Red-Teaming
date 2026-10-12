namespace ProfileStore.Benchmark;

public sealed class Checksum
{
  ulong Value = 14_695_981_039_346_656_037UL;

  public void Add(long value)
  {
    Add((ulong)value);
  }

  public void Add(int value)
  {
    Add((ulong)(uint)value);
  }

  public void Add(string value)
  {
    foreach (var ch in value)
      Add(ch);
  }

  public void Add(UserProfile profile)
  {
    Add(profile.UserId);
    Add(profile.Email);
    Add(profile.Country);
    Add(profile.Status);
    Add(profile.CreatedAtUnixMs);
    Add(profile.LastLoginUnixMs);
    Add(profile.Reputation);
  }

  public string Hex => Value.ToString("X16");

  void Add(ulong value)
  {
    Value ^= value;
    Value *= 1_099_511_628_211UL;
  }
}
