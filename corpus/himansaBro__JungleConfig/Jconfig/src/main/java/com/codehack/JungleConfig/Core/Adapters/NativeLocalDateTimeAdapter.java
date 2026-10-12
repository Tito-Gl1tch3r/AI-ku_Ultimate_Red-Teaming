package com.codehack.JungleConfig.Core.Adapters;

import com.codehack.JungleConfig.Core.TypeConverterAdapter;
import java.time.LocalDateTime;

public class NativeLocalDateTimeAdapter implements TypeConverterAdapter {
    @Override
    public String getType() {
        return LocalDateTime.class.getSimpleName();
    }

    @Override
    public String ConvertToSave(Object object) {
        return object.toString();
    }

    @Override
    public Object CastToUse(String data) {
        return LocalDateTime.parse(data);
    }
}
