namespace ProfileStore.Benchmark;

public sealed record WorkloadPlan(
    long[] PointReadIds,
    long[] EmailReadIds,
    CountryStatusQuery[] CountryStatusQueries,
    CreatedAtRangeQuery[] CreatedAtRangeQueries,
    long[] UpdateIds,
    long[] PostPointReadIds,
    long[] PostEmailReadIds,
    CountryStatusQuery[] PostCountryStatusQueries);

public static class WorkloadPlanner
{
  public static WorkloadPlan Create(BenchmarkConfig config, ProfileGenerator generator)
  {
    var random = new Random(config.Seed);
    return new WorkloadPlan(
        CreateIds(config.ReadCount, config.Profiles, random),
        CreateIds(config.EmailReadCount, config.Profiles, random),
        CreateCountryStatusQueries(config.QueryCount, generator, random),
        CreateCreatedAtRanges(config.QueryCount, config.Profiles, generator, random),
        CreateIds(config.UpdateCount, config.Profiles, random),
        CreateIds(config.PostReadCount, config.Profiles, random),
        CreateIds(config.PostEmailReadCount, config.Profiles, random),
        CreateCountryStatusQueries(config.PostQueryCount, generator, random));
  }

  static long[] CreateIds(int count, int maxId, Random random)
  {
    var ids = new long[count];
    for (var i = 0; i < ids.Length; i++)
      ids[i] = random.NextInt64(1, maxId + 1L);
    return ids;
  }

  static CountryStatusQuery[] CreateCountryStatusQueries(
      int count,
      ProfileGenerator generator,
      Random random)
  {
    var countries = generator.CountryCodes;
    var statuses = generator.StatusValues;
    var queries = new CountryStatusQuery[count];
    for (var i = 0; i < queries.Length; i++)
    {
      var country = countries[random.Next(0, countries.Count)];
      var status = statuses[random.Next(0, statuses.Count)];
      queries[i] = new CountryStatusQuery(country, status);
    }
    return queries;
  }

  static CreatedAtRangeQuery[] CreateCreatedAtRanges(
      int count,
      int maxId,
      ProfileGenerator generator,
      Random random)
  {
    var queries = new CreatedAtRangeQuery[count];
    for (var i = 0; i < queries.Length; i++)
    {
      var startId = random.NextInt64(1, Math.Max(2, maxId - 5_000));
      var from = generator.Create(startId).CreatedAtUnixMs;
      var to = generator.Create(Math.Min(maxId, startId + 5_000)).CreatedAtUnixMs;
      queries[i] = new CreatedAtRangeQuery(from, to);
    }
    return queries;
  }
}
