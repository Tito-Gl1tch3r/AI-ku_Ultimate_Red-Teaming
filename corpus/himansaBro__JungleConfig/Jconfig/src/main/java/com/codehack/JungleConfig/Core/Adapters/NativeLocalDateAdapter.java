package com.codehack.JungleConfig.Core.Adapters;

import com.codehack.JungleConfig.Core.TypeConverterAdapter;
import java.time.LocalDate;

public class NativeLocalDateAdapter implements TypeConverterAdapter {
    @Override
    public String getType() {
        return LocalDate.class.getSimpleName();
    }

    @Override
    public String ConvertToSave(Object object) {
        return object.toString();
    }

    @Override
    public Object CastToUse(String data) {
        return LocalDate.parse(data);
    }
}
