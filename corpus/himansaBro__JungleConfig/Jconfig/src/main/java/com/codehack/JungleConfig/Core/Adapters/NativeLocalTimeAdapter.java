package com.codehack.JungleConfig.Core.Adapters;

import com.codehack.JungleConfig.Core.TypeConverterAdapter;
import java.time.LocalTime;

public class NativeLocalTimeAdapter implements TypeConverterAdapter {
    @Override
    public String getType() {
        return LocalTime.class.getSimpleName();
    }

    @Override
    public String ConvertToSave(Object object) {
        return object.toString();
    }

    @Override
    public Object CastToUse(String data) {
        return LocalTime.parse(data);
    }
}
