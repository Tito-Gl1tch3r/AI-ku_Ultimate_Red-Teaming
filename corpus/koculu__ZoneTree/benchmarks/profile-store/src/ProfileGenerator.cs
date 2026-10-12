using System.Text;

namespace ProfileStore.Benchmark;

public sealed class ProfileGenerator(int seed)
{
  static readonly string[] Countries =
  [
    "US", "DE", "GB", "FR", "NL", "SE", "NO", "DK",
    "FI", "ES", "IT", "PT", "PL", "CZ", "TR", "JP",
    "KR", "SG", "IN", "BR", "CA", "AU", "MX", "AR",
    "ZA", "IL", "IE", "CH", "AT", "BE", "RO", "GR"
  ];

  static readonly string[] Statuses = ["active", "suspended", "deleted", "pending"];

  const long BaseCreatedAt = 1_672_531_200_000; // 2023-01-01 UTC

  readonly ulong Seed = (uint)seed;

  public IReadOnlyList<string> CountryCodes => Countries;

  public IReadOnlyList<string> StatusValues => Statuses;

  public UserProfile Create(long userId)
  {
    var a = Mix((ulong)userId + Seed);
    var b = Mix(a + 0x9E3779B97F4A7C15UL);
    var country = Countries[(int)(a % (ulong)Countries.Length)];
    var status = Statuses[(int)((a >> 8) % (ulong)Statuses.Length)];
    var bucket = userId % 97;
    var createdAt = BaseCreatedAt + userId * 1_000 + (long)(a % 997);
    var lastLogin = BaseCreatedAt + (long)(b % (90UL * 24 * 60 * 60 * 1000));
    var reputation = (int)(b % 1_000_000);

    return new UserProfile(
        userId,
        $"user{userId:D12}@example{bucket:D2}.com",
        country,
        status,
        createdAt,
        lastLogin,
        reputation,
        $"User {userId:D12}",
        CreateBio(userId, a, b));
  }

  public UserProfile Update(UserProfile current)
  {
    var mixed = Mix((ulong)current.UserId + Seed + 0xD1B54A32D192ED03UL);
    var status = current.UserId % 4 == 0
        ? Statuses[(Array.IndexOf(Statuses, current.Status) + 1) % Statuses.Length]
        : current.Status;
    var reputationDelta = (int)(mixed % 501) - 250;
    var reputation = Math.Clamp(current.Reputation + reputationDelta, 0, 1_000_000);
    var lastLogin = current.LastLoginUnixMs + 7 * 24 * 60 * 60 * 1000 + (long)(mixed % 86_400_000);

    return current with
    {
      Status = status,
      Reputation = reputation,
      LastLoginUnixMs = lastLogin,
      Bio = current.Bio + " updated"
    };
  }

  static string CreateBio(long userId, ulong a, ulong b)
  {
    var builder = new StringBuilder(256);
    builder.Append("Profile ");
    builder.Append(userId);
    builder.Append(" prefers ");
    builder.Append((a % 5) switch
    {
      0 => "storage engines",
      1 => "distributed systems",
      2 => "analytics",
      3 => "developer tools",
      _ => "backend services"
    });
    builder.Append(" and has segment ");
    builder.Append((b % 10_000).ToString("D4"));
    builder.Append('.');
    return builder.ToString();
  }

  static ulong Mix(ulong value)
  {
    value += 0x9E3779B97F4A7C15UL;
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9UL;
    value = (value ^ (value >> 27)) * 0x94D049BB133111EBUL;
    return value ^ (value >> 31);
  }
}
