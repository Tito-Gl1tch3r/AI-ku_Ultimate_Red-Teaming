package io.vacco.metolithe.core;

import io.vacco.metolithe.annotations.MtFk;
import io.vacco.metolithe.annotations.MtIndex;
import io.vacco.metolithe.annotations.MtPk;
import io.vacco.metolithe.annotations.MtUnique;

import java.lang.annotation.Annotation;
import java.util.*;
import java.util.function.BiConsumer;
import java.util.function.Function;
import java.util.stream.Stream;

import static io.vacco.metolithe.core.MtErr.*;
import static java.lang.String.format;
import static java.lang.reflect.Modifier.*;
import static java.util.stream.Collectors.toList;

public class MtDescriptor<T> {

  private static final String BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz";
  private static final int MAX_VALUE_2 = 1296; // 36^2
  private static final int Length = 2;

  private static final Object[] empty = new Object[]{};

  private final Class<T> cl;
  private final MtCaseFormat fmt;

  private final List<MtFieldDescriptor> fields;
  private final List<MtFieldDescriptor> fieldsNoPk;
  private final MtFieldDescriptor pkField;

  @SuppressWarnings("this-escape")
  public MtDescriptor(Class<T> entity, MtCaseFormat fmt) {
    this.cl = Objects.requireNonNull(entity);
    this.fmt = Objects.requireNonNull(fmt);
    this.fields = new ArrayList<>();
    int k = 0;
    for (var f : entity.getFields()) {
      if (isPublic(f.getModifiers()) && !isStatic(f.getModifiers()) && !isTransient(f.getModifiers())) {
        this.fields.add(new MtFieldDescriptor(k, f, fmt, this));
        k++;
      }
    }

    this.fieldsNoPk = this.fields.stream().filter(fd -> !fd.isPk()).collect(toList());
    var pkds = this.fields.stream().filter(MtFieldDescriptor::isPk).collect(toList());
    if (pkds.size() > 1) {
      throw badPkDefinitions(pkds);
    }
    this.pkField = pkds.isEmpty() ? null : pkds.get(0);
  }

  public String getTableName(String schema) {
    var raw = String.format("%s.%s", schema, getFormat().of(cl.getSimpleName()));
    return getFormat().of(raw);
  }

  public String getAlias() {
    int hash = Math.abs(Objects.requireNonNull(cl.getCanonicalName()).hashCode());
    hash = hash % MAX_VALUE_2; // Reduce to fit within base-36^2 range
    var result = new char[Length + 1];
    for (int i = Length; i > 0; i--) {
      result[i] = BASE36_CHARS.charAt(hash % 36);
      hash /= 36;
    }
    result[0] = '_';
    return new String(result);
  }

  @SuppressWarnings("unchecked")
  public <E extends Enum<?>> List<Class<E>> getEnumFields() {
    return fields.stream()
      .filter(fd -> Enum.class.isAssignableFrom(fd.getType()))
      .map(fd -> (Class<E>) fd.getType())
      .collect(toList());
  }

  public Optional<MtFieldDescriptor> getForeignKeyTo(Class<?> target) {
    return fields.stream()
      .filter(fd ->
        fd.get(MtFk.class)
          .map(mtFk -> mtFk.value().equals(target))
          .orElse(false)
      ).findFirst();
  }

  public Optional<MtFieldDescriptor> getForeignKeyTo(MtDescriptor<?> target) {
    var fk = getForeignKeyTo(target.getType());
    if (fk.isPresent()) {
      return fk;
    }
    return target.getForeignKeyTo(this.getType());
  }

  public Stream<MtFieldDescriptor> get(Class<? extends Annotation> target) {
    return fields.stream().filter(fd -> fd.get(target).isPresent());
  }

  private Map<Integer, List<MtFieldDescriptor>> indexFields(Function<MtFieldDescriptor, Integer> idxFn) {
    var out = new TreeMap<Integer, List<MtFieldDescriptor>>();
    for (var fd : fieldsNoPk) {
      var idx = idxFn.apply(fd);
      if (idx != null) {
        out.computeIfAbsent(idx, k -> new ArrayList<>()).add(fd);
      }
    }
    return out;
  }

  public Map<Integer, List<MtFieldDescriptor>> getIndices() {
    return indexFields(fd ->
      fd.get(MtIndex.class)
        .map(MtIndex::idx)
        .orElse(null)
    );
  }

  public Map<Integer, List<MtFieldDescriptor>> getUniqueConstraints() {
    return indexFields(fd ->
      fd.get(MtUnique.class)
        .map(MtUnique::idx)
        .orElse(null)
    );
  }

  public Object[] getPkValues(T t) {
    if (t == null || this.pkField == null) {
      return empty;
    }
    var pkValues = new TreeMap<>();
    for (var fd : fields) {
      var ou = fd.get(MtPk.class);
      if (ou.isPresent() && ou.get().idx() != -1) {
        var comp = fd.getValue(t);
        if (comp == null) {
          throw badPkComponent(t, fd);
        }
        pkValues.put(ou.get().idx(), comp);
      }
    }
    return pkValues.values().toArray();
  }

  public List<MtFieldDescriptor> getFields(boolean withPk) {
    return withPk ? fields : fieldsNoPk;
  }

  public void forEach(boolean withPk, Object t, BiConsumer<String, Object> entryFn) {
    for (var fd : getFields(withPk)) {
      entryFn.accept(fd.getFieldName(), fd.getValue(t));
    }
  }

  public boolean matches(Class<?> other) {
    return cl == other;
  }

  public Optional<MtFieldDescriptor> getPkField() {
    return pkField != null ? Optional.of(pkField) : Optional.empty();
  }

  public MtFieldDescriptor getField(String name) {
    return fields.stream()
      .filter(fd -> fd.getFieldName().equalsIgnoreCase(name)).findFirst()
      .orElseThrow(() -> badField(name, this));
  }

  public Class<T> getType() {
    return cl;
  }

  public String getClassName() {
    return cl.getCanonicalName();
  }

  public String getName() {
    return fmt.of(cl.getSimpleName());
  }

  public MtCaseFormat getFormat() {
    return fmt;
  }

  @Override
  public String toString() {
    return format("<%s>%s", cl.getSimpleName(), fields);
  }

}
