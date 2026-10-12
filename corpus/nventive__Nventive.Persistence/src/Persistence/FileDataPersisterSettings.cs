namespace Nventive.Persistence
{
	/// <summary>
	/// Provides settings for persisting data
	/// </summary>
	public class FileDataPersisterSettings
	{
		/// <summary>
		/// Default instance of <see cref="FileDataPersisterSettings"/> 
		/// </summary>
		public static FileDataPersisterSettings Default { get; } = new FileDataPersisterSettings();

		/// <summary>
		/// Constructor with default values
		/// </summary>
		/// <param name="numberOfRetries">Max number of retry</param>
		/// <param name="retryDelay">Delay between each retry</param>
		/// <param name="exclusiveMode">To be added</param>
		public FileDataPersisterSettings(
			int numberOfRetries = 3,
			int retryDelay = 100,
			bool exclusiveMode = true)
		{
			NumberOfRetries = numberOfRetries;
			RetryDelay = retryDelay;
			ExclusiveMode = exclusiveMode;
		}

		/// <summary>
		/// The number of retries if persisting fails
		/// </summary>
		public int NumberOfRetries { get; }

		/// <summary>
		/// The delay between each retry
		/// </summary>
		public int RetryDelay { get; }

		/// <summary>
		/// To be added
		/// </summary>
		public bool ExclusiveMode { get; }
	}
}
