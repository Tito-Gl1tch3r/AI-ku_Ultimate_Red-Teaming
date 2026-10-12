package net.robinfriedli.jxp.api;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.function.Function;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.exceptions.ConversionException;

public class StringConverter {

    private static final List<StringConversionContribution<?>> stringConversions = Lists.newArrayList();

    static {
        stringConversions.add(new StringConversionContribution<>(0, Integer.class, Integer::parseInt, Object::toString));
        stringConversions.add(new StringConversionContribution<>(0D, Double.class, Double::parseDouble, Object::toString));
        stringConversions.add(new StringConversionContribution<>(0F, Float.class, Float::parseFloat, Object::toString));
        stringConversions.add(new StringConversionContribution<>(0L, Long.class, Long::parseLong, Object::toString));
        stringConversions.add(new StringConversionContribution<>(false, Boolean.class, Boolean::parseBoolean, Object::toString));
        stringConversions.add(new StringConversionContribution<>(BigDecimal.ZERO, BigDecimal.class, BigDecimal::new, BigDecimal::toString));
        stringConversions.add(new StringConversionContribution<>("", String.class, String::toString, String::toString));
    }


    public static <V> V convert(String s, Class<V> target) throws ConversionException {
        StringConversionContribution<V> converter = getConverter(target);

        try {
            return converter.convert(s);
        } catch (Exception e) {
            throw new ConversionException(e);
        }
    }

    @SuppressWarnings("unchecked")
    public static <V> String reverse(V objectToReverse) throws ConversionException {
        StringConversionContribution<V> converter = (StringConversionContribution<V>) getConverter(objectToReverse.getClass());
        try {
            return converter.reverse(objectToReverse);
        } catch (Exception e) {
            throw new ConversionException(e);
        }
    }

    public static <V> void map(V emptyValue, Class<V> targetClass, Function<String, V> conversionFunc, Function<V, String> reverseFunc) {
        if (!canConvert(targetClass)) {
            stringConversions.add(new StringConversionContribution<>(emptyValue, targetClass, conversionFunc, reverseFunc));
        }
    }

    public static boolean canConvert(Class<?> target) {
        return stringConversions.stream().anyMatch(c -> c.getClassToConvert().equals(target));
    }

    public static <V> V getEmptyValue(Class<V> classToConvert) {
        return getConverter(classToConvert).getEmptyValue();
    }

    @SuppressWarnings("unchecked")
    private static <V> StringConversionContribution<V> getConverter(Class<V> classToConvert) {
        Optional<StringConversionContribution<?>> stringConverter = stringConversions
            .stream()
            .filter(c -> c.getClassToConvert().equals(classToConvert))
            .findFirst();

        if (stringConverter.isPresent()) {
            return (StringConversionContribution<V>) stringConverter.get();
        } else {
            throw new IllegalStateException("No conversion available for class " + classToConvert.getSimpleName()
                + ". Add with StringConverter#map");
        }
    }

}
