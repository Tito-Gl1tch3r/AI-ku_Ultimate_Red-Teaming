package io.vacco.metolithe.util;

import java.util.List;
import java.util.Objects;

public class MtPage2<T, K1, K2> {

  public long     size;
  public List<T>  items;
  public K1       nx1;
  public K2       nx2;

  public boolean hasNext() {
    return nx1 != null && nx2 != null;
  }

  public static <T, K1, K2> MtPage2<T, K1, K2> of(long size, List<T> items, K1 nx1, K2 nx2) {
    var p = new MtPage2<T, K1, K2>();
    p.size = size;
    p.items = Objects.requireNonNull(items);
    p.nx1 = Objects.requireNonNull(nx1);
    p.nx2 = Objects.requireNonNull(nx2);
    return p;
  }

}
