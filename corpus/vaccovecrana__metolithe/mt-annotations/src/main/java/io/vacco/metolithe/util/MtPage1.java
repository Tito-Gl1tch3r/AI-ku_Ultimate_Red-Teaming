package io.vacco.metolithe.util;

import java.util.List;
import java.util.Objects;

public class MtPage1<T, K1> {

  public long     size;
  public List<T>  items;
  public K1       nx1;

  public boolean hasNext() {
    return nx1 != null;
  }

  public static <T, K1> MtPage1<T, K1> of(long size, List<T> items, K1 nx1) {
    var p = new MtPage1<T, K1>();
    p.size = size;
    p.items = Objects.requireNonNull(items);
    p.nx1 = nx1;
    return p;
  }

  public static <T, K1> MtPage1<T, K1> ofList(List<T> items, K1 nx1) {
    return of(items.size(), items, nx1);
  }

  public static <T, K1> MtPage1<T, K1> ofSingle(T item) {
    return ofList(List.of(item), null);
  }

}
