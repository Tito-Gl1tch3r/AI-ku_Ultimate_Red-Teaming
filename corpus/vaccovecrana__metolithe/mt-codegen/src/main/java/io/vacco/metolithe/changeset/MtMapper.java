package io.vacco.metolithe.changeset;

import io.vacco.metolithe.annotations.*;
import io.vacco.metolithe.core.*;
import io.vacco.oriax.alg.OxKos;
import io.vacco.oriax.core.*;
import java.util.*;
import java.util.stream.*;

import static io.vacco.metolithe.core.MtErr.*;
import static io.vacco.metolithe.core.MtUtil.*;
import static io.vacco.metolithe.id.MtMurmur3.*;
import static java.lang.String.format;
import static java.lang.Integer.toHexString;

public class MtMapper {

  private MtCol mapColumn(MtFieldDescriptor d) {
    var c = new MtCol();
    c.name = d.getFieldName();
    c.type = d.getFormat().of(sqlTypeOf(d));
    if (d.isPk()) {
      c.primaryKey = true;
      c.nullable = false;
    } else {
      c.primaryKey = false;
      c.nullable = d.get(MtNotNull.class).isEmpty();
    }
    return c;
  }

  private MtIdx mapIndex(MtDescriptor<?> d, List<MtFieldDescriptor> components) {
    var fields = components.stream().map(MtFieldDescriptor::getFieldName).toArray();
    var hash = toHexString(hash32(toStringConcat(fields).orElseThrow(), DEFAULT_SEED));
    var idx = new MtIdx();
    idx.name = d.getFormat().of(format("idx_%s_%s", d.getName(), hash));
    for (var fd : components) {
      idx.columns.add(fd.getFieldName());
    }
    return idx;
  }

  private MtUnq mapUnique(MtDescriptor<?> d, List<MtFieldDescriptor> components) {
    var fields = components.stream().map(MtFieldDescriptor::getFieldName).toArray();
    var hash = toHexString(hash32(toStringConcat(fields).orElseThrow(), DEFAULT_SEED));
    var unq = new MtUnq();
    unq.name = d.getFormat().of(format("unq_%s_%s", d.getName(), hash));
    for (var fd : components) {
      unq.columns.add(fd.getFieldName());
    }
    return unq;
  }

  private MtFkey mapForeignKey(MtDescriptor<?> d, MtFieldDescriptor fd) {
    var mfk = new MtFkey();
    var fk = fd.get(MtFk.class).orElseThrow();
    var fkTarget = new MtDescriptor<>(fk.value(), fd.getFormat());
    var targetPk = fkTarget.get(MtPk.class).findFirst().orElseThrow();

    if (!fd.getType().equals(targetPk.getType())) {
      throw badForeignKey(
        d.getName(), fd.getFieldName(), fd.getType().getTypeName(),
        fkTarget.getName(), targetPk.getFieldName(), targetPk.getType().getTypeName()
      );
    }

    var from = d.getName();
    var fromCol = fd.getFieldName();
    var to = fkTarget.getName();
    var toCol = targetPk.getFieldName();
    var hash = toHexString(hash32(toStringConcat(from, fromCol, to, toCol).orElseThrow(), DEFAULT_SEED));

    mfk.name = format("fk_%s_%s", d.getName(), hash);
    mfk.to = to;
    mfk.fromCol = fromCol;
    mfk.toCol = toCol;

    return mfk;
  }

  public MtTable mapTable(MtDescriptor<?> d) {
    var t = new MtTable();
    t.name = d.getName();
    for (var fd : d.getFields(true)) {
      t.columns.add(mapColumn(fd));
    }
    for (var e : d.getIndices().entrySet()) {
      if (e.getKey() == -1) {
        for (var singleIdx : e.getValue()) {
          t.indices.add(mapIndex(d, List.of(singleIdx)));
        }
      } else {
        t.indices.add(mapIndex(d, e.getValue()));
      }
    }
    for (var e : d.getUniqueConstraints().entrySet()) {
      if (e.getKey() == -1) {
        for (var singleUnq : e.getValue()) {
          t.unique.add(mapUnique(d, List.of(singleUnq)));
        }
      } else {
        t.unique.add(mapUnique(d, e.getValue()));
      }
    }
    d.get(MtFk.class).forEach(fk -> t.fKeys.add(mapForeignKey(d, fk)));
    return t;
  }

  public List<MtTable> build(MtCaseFormat fmt, Class<?> ... schemaClasses) {
    var descriptors = Arrays.stream(schemaClasses)
      .map(clazz -> new MtDescriptor<>(clazz, fmt))
      .map(fd -> new OxVtx<String, MtDescriptor<?>>(fd.getName(), fd))
      .collect(Collectors.toList());
    var schema = new OxGrph<String, MtDescriptor<?>>();
    var out = new ArrayList<MtTable>();
    var processed = new java.util.HashSet<String>();

    for (var vd : descriptors) {
      for (var fd : vd.data.getFields(true)) {
        var ofk = fd.get(MtFk.class);
        if (ofk.isPresent()) {
          for (var v : descriptors) {
            if (v.data.matches(ofk.get().value())) {
              schema.addEdge(vd, v);
            }
          }
        }
      }
    }

    OxKos.apply(schema).forEach((k, v) -> {
      for (var vtx : v) {
        processed.add(vtx.data.getName());
        out.add(mapTable(vtx.data));
      }
    });

    // Include isolated classes (no FKs) that were not part of the graph
    for (var vd : descriptors) {
      if (!processed.contains(vd.data.getName())) {
        out.add(mapTable(vd.data));
      }
    }

    return out;
  }

}
