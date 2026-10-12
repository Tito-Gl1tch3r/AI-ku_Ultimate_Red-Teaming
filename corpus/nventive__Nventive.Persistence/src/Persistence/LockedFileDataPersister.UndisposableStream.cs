using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	public partial class LockedFileDataPersister<T>
	{
		private class UndisposableStream : Stream
		{
			private readonly Stream _stream;

			public UndisposableStream(Stream stream)
			{
				_stream = stream;
			}

			public override void Flush()
			{
				_stream.Flush();
			}

			public override long Seek(long offset, SeekOrigin origin)
			{
				return _stream.Seek(offset, origin);
			}

			public override void SetLength(long value)
			{
				_stream.SetLength(value);
			}

			public override int Read(byte[] buffer, int offset, int count)
			{
				return _stream.Read(buffer, offset, count);
			}

			public override Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken)
			{
				return _stream.ReadAsync(buffer, offset, count, cancellationToken);
			}

			public override void Write(byte[] buffer, int offset, int count)
			{
				_stream.Write(buffer, offset, count);
			}

			public override Task WriteAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken)
			{
				return _stream.WriteAsync(buffer, offset, count, cancellationToken);
			}

			public override bool CanRead => _stream.CanRead;

			public override bool CanSeek => _stream.CanSeek;

			public override bool CanWrite => _stream.CanWrite;

			public override long Length => _stream.Length;

			public override long Position
			{
				get => _stream.Position;
				set => _stream.Position = value;
			}

			protected override void Dispose(bool disposing)
			{
				// do nothing
			}
		}
	}
}
