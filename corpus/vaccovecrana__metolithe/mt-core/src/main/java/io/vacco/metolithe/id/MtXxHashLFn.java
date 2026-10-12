package io.vacco.metolithe.id;

import io.vacco.metolithe.core.MtUtil;

import static io.vacco.metolithe.id.MtXxHash.DEFAULT_SEED;
import static io.vacco.metolithe.id.MtXxHash.hash64;
import static java.util.Objects.requireNonNull;

public class MtXxHashLFn implements MtIdFn<Long> {

  private final int seed;

  public MtXxHashLFn(int seed) {
    this.seed = seed;
  }

  public MtXxHashLFn() {
    this.seed = DEFAULT_SEED;
  }

  @Override
  public Long apply(Object[] parts) {
    return MtUtil.toStringConcat(requireNonNull(parts))
      .map(ba -> hash64(ba, 0, ba.length, this.seed))
      .orElseThrow(IllegalStateException::new);
  }

  @Override
  public Class<Long> getIdType() {
    return Long.class;
  }

}
