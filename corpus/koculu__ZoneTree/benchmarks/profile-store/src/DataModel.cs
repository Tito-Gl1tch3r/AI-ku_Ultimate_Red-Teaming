using System.Globalization;

namespace ProfileStore.Benchmark;

public sealed record UserProfile(
    long UserId,
    string Email,
    string Country,
    string Status,
    long CreatedAtUnixMs,
    long LastLoginUnixMs,
    int Reputation,
    string DisplayName,
    string Bio);

public sealed record CountryStatusQuery(string Country, string Status);

public sealed record CreatedAtRangeQuery(long FromUnixMs, long ToUnixMs);

public static class ProfileCodec
{
  public static string Serialize(UserProfile profile)
  {
    return string.Join('|',
        profile.UserId.ToString(CultureInfo.InvariantCulture),
        profile.Email,
        profile.Country,
        profile.Status,
        profile.CreatedAtUnixMs.ToString(CultureInfo.InvariantCulture),
        profile.LastLoginUnixMs.ToString(CultureInfo.InvariantCulture),
        profile.Reputation.ToString(CultureInfo.InvariantCulture),
        profile.DisplayName,
        profile.Bio);
  }

  public static UserProfile Deserialize(string value)
  {
    var parts = value.Split('|', 9);
    return new UserProfile(
        long.Parse(parts[0], CultureInfo.InvariantCulture),
        parts[1],
        parts[2],
        parts[3],
        long.Parse(parts[4], CultureInfo.InvariantCulture),
        long.Parse(parts[5], CultureInfo.InvariantCulture),
        int.Parse(parts[6], CultureInfo.InvariantCulture),
        parts[7],
        parts[8]);
  }
}

public static class ProfileKeys
{
  const int MaxReputation = 1_000_000;

  public static string CountryStatus(UserProfile profile) =>
      CountryStatus(profile.Country, profile.Status, profile.UserId);

  public static string CountryStatus(string country, string status, long userId) =>
      $"{country}|{status}|{userId:D20}";

  public static string CountryStatusPrefix(string country, string status) =>
      $"{country}|{status}|";

  public static string CreatedAt(UserProfile profile) =>
      $"{profile.CreatedAtUnixMs:D20}|{profile.UserId:D20}";

  public static string CreatedAt(long createdAtUnixMs, long userId) =>
      $"{createdAtUnixMs:D20}|{userId:D20}";

  public static string Reputation(UserProfile profile) =>
      $"{MaxReputation - profile.Reputation:D10}|{profile.UserId:D20}";
}
