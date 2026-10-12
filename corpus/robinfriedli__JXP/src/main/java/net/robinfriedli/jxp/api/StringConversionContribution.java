package net.robinfriedli.jxp.api;

import java.util.function.Function;

public class StringConversionContribution<C> {

    private final C emptyValue;
    private final Class<C> classToConvert;
    private final Function<String, C> conversionFunction;
    private final Function<C, String> reverseFunction;

    public StringConversionContribution(C emptyValue, Class<C> classToConvert, Function<String, C> conversionFunction, Function<C, String> reverseFunction) {
        this.emptyValue = emptyValue;
        this.classToConvert = classToConvert;
        this.conversionFunction = conversionFunction;
        this.reverseFunction = reverseFunction;
    }

    public C getEmptyValue() {
        return emptyValue;
    }

    public Class<C> getClassToConvert() {
        return classToConvert;
    }

    public C convert(String s) {
        return conversionFunction.apply(s);
    }

    public String reverse(C objectToStringify) {
        return reverseFunction.apply(objectToStringify);
    }
}
