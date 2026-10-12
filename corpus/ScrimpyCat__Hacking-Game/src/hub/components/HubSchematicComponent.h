/*
 *  Copyright (c) 2019, Stefan Johnson
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without modification,
 *  are permitted provided that the following conditions are met:
 *
 *  1. Redistributions of source code must retain the above copyright notice, this list
 *     of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright notice, this
 *     list of conditions and the following disclaimer in the documentation and/or other
 *     materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#ifndef HackingGame_HubSchematicComponent_h
#define HackingGame_HubSchematicComponent_h

#include "Base.h"
#include "HubArchPort.h"
#include "HubSystem.h"

#define HK_HUB_SCHEMATIC_COMPONENT_ID (HKHubTypeSchematic | HK_HUB_COMPONENT_FLAG)

#define HK_HUB_SCHEMATIC_SLOT_MAX 15

#define HK_HUB_SCHEMATIC_SLOT_PIN_MAX 154

typedef struct {
    uint8_t slot[2];
    uint8_t pin[2];
    struct {
        uint8_t moves[7];
        uint8_t turns;
    } path;
} HKHubSchematicWiring;

typedef struct {
    CCEntity device;
    
} HKHubSchematicSlot;

typedef struct {
    CC_COMPONENT_INHERIT(CCComponentClass);
    _Bool editable;
    _Bool debuggable;
    CCArray(HKHubSchematicWiring) wirings;
    CCEntity slots[HK_HUB_SCHEMATIC_SLOT_MAX];
} HKHubSchematicComponentClass, *HKHubSchematicComponentPrivate;


void HKHubSchematicComponentRegister(void);
void HKHubSchematicComponentDeregister(void);
void HKHubSchematicComponentDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);

/*!
 * @brief Initialize the schematic component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubSchematicComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the schematic component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubSchematicComponentDeallocate(CCComponent Component);

/*!
 * @brief Get whether the schematic is editable.
 * @param Component The schematic component.
 * @return Whether the schematic can be edited.
 */
static inline _Bool HKHubSchematicComponentGetIsEditable(CCComponent Component);

/*!
 * @brief Set whether the schematic is editable or not.
 * @param Component The schematic component.
 * @param Editable Whether the schematic is editable or not.
 */
static inline void HKHubSchematicComponentSetIsEditable(CCComponent Component, _Bool Editable);

/*!
 * @brief Get whether the schematic is debuggable.
 * @param Component The schematic component.
 * @return Whether the schematic can be debugged.
 */
static inline _Bool HKHubSchematicComponentGetIsDebuggable(CCComponent Component);

/*!
 * @brief Set whether the schematic is debuggable or not.
 * @param Component The schematic component.
 * @param Debuggable Whether the schematic can be debugged or not.
 */
static inline void HKHubSchematicComponentSetIsDebuggable(CCComponent Component, _Bool Debuggable);

/*!
 * @brief Get the wiring for a given slot pin in the schematic.
 * @param Component The schematic component.
 * @param SlotIndex The slot index. Must be less than @b HK_HUB_SCHEMATIC_SLOT_MAX.
 * @param Pin The pin. Must be less than @b HK_HUB_SCHEMATIC_SLOT_PIN_MAX.
 * @return The device entity at that slot or NULL if there is none.
 */
static inline const HKHubSchematicWiring *HKHubSchematicComponentGetWiring(CCComponent Component, uint8_t SlotIndex, uint8_t Pin);

/*!
 * @brief Remove the wiring for a given slot pin in the schematic.
 * @param Component The schematic component.
 * @param SlotIndex The slot index. Must be less than @b HK_HUB_SCHEMATIC_SLOT_MAX.
 * @param Pin The pin. Must be less than @b HK_HUB_SCHEMATIC_SLOT_PIN_MAX.
 */
static inline void HKHubSchematicComponentRemoveWiring(CCComponent Component, uint8_t SlotIndex, uint8_t Pin);

/*!
 * @brief Set the wiring for a given slot pin in the schematic.
 * @description If the pin or end pin is already wired it will remove those old wirings.
 * @warning Any previous wirings received from HKHubSchematicComponentGetWiring should be discarded.
 * @param Component The schematic component.
 * @param Wiring The wiring to add to the schematic.
 */
static inline void HKHubSchematicComponentSetWiring(CCComponent Component, HKHubSchematicWiring Wiring);

/*!
 * @brief Get the device entity in the schematic's slot.
 * @param Component The schematic component.
 * @param Index The slot index. Must be less than @b HK_HUB_SCHEMATIC_SLOT_MAX.
 * @return The device entity at that slot or NULL if there is none.
 */
static inline CCEntity HKHubSchematicComponentGetSlot(CCComponent Component, uint8_t Index);

/*!
 * @brief Set the number of device slots the schematic has.
 * @param Component The schematic component.
 * @param Device The device to put in the slot, or NULL to remove the current device. Ownership is transferred to the component.
 * @param Index The slot index. Must be less than @b HK_HUB_SCHEMATIC_SLOT_MAX.
 */
static inline void HKHubSchematicComponentSetSlot(CCComponent Component, CCEntity CC_OWN(Device), uint8_t Index);


#pragma mark -

static inline void HKHubSchematicComponentInitialize(CCComponent Component, CCComponentID id)
{
    CCComponentInitialize(Component, id);
    ((HKHubSchematicComponentPrivate)Component)->editable = FALSE;
    ((HKHubSchematicComponentPrivate)Component)->debuggable = FALSE;
    ((HKHubSchematicComponentPrivate)Component)->wirings = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubSchematicWiring), 4);
    memset(((HKHubSchematicComponentPrivate)Component)->slots, 0, sizeof(((HKHubSchematicComponentPrivate)Component)->slots));
}

static inline void HKHubSchematicComponentDeallocate(CCComponent Component)
{
    CCArrayDestroy(((HKHubSchematicComponentPrivate)Component)->wirings);
    
    for (size_t Loop = 0; Loop < HK_HUB_SCHEMATIC_SLOT_MAX; Loop++)
    {
        if (((HKHubSchematicComponentPrivate)Component)->slots[Loop]) CCEntityDestroy(((HKHubSchematicComponentPrivate)Component)->slots[Loop]);
    }
    
    CCComponentDeallocate(Component);
}

static inline _Bool HKHubSchematicComponentGetIsEditable(CCComponent Component)
{
    return ((HKHubSchematicComponentPrivate)Component)->editable;
}

static inline void HKHubSchematicComponentSetIsEditable(CCComponent Component, _Bool Editable)
{
    ((HKHubSchematicComponentPrivate)Component)->editable = Editable;
}

static inline _Bool HKHubSchematicComponentGetIsDebuggable(CCComponent Component)
{
    return ((HKHubSchematicComponentPrivate)Component)->debuggable;
}

static inline void HKHubSchematicComponentSetIsDebuggable(CCComponent Component, _Bool Debuggable)
{
    ((HKHubSchematicComponentPrivate)Component)->debuggable = Debuggable;
}

static inline const HKHubSchematicWiring *HKHubSchematicComponentGetWiring(CCComponent Component, uint8_t SlotIndex, uint8_t Pin)
{
    CCAssertLog(SlotIndex < HK_HUB_SCHEMATIC_SLOT_MAX, "SlotIndex must be less than HK_HUB_SCHEMATIC_SLOT_MAX");
    CCAssertLog(Pin < HK_HUB_SCHEMATIC_SLOT_PIN_MAX, "Pin must be less than HK_HUB_SCHEMATIC_SLOT_PIN_MAX");
    
    for (size_t Loop = 0, Count = CCArrayGetCount(((HKHubSchematicComponentPrivate)Component)->wirings); Loop < Count; Loop++)
    {
        HKHubSchematicWiring *CurrentWiring = CCArrayGetElementAtIndex(((HKHubSchematicComponentPrivate)Component)->wirings, Loop);
        
        if (((CurrentWiring->slot[0] == SlotIndex) && (CurrentWiring->pin[0] == Pin)) || ((CurrentWiring->slot[1] == SlotIndex) && (CurrentWiring->pin[1] == Pin)))
        {
            return CurrentWiring;
        }
    }
    
    return NULL;
}

static inline void HKHubSchematicComponentRemoveWiring(CCComponent Component, uint8_t SlotIndex, uint8_t Pin)
{
    CCAssertLog(SlotIndex < HK_HUB_SCHEMATIC_SLOT_MAX, "SlotIndex must be less than HK_HUB_SCHEMATIC_SLOT_MAX");
    CCAssertLog(Pin < HK_HUB_SCHEMATIC_SLOT_PIN_MAX, "Pin must be less than HK_HUB_SCHEMATIC_SLOT_PIN_MAX");
    
    for (size_t Loop = 0, Count = CCArrayGetCount(((HKHubSchematicComponentPrivate)Component)->wirings); Loop < Count; Loop++)
    {
        HKHubSchematicWiring *CurrentWiring = CCArrayGetElementAtIndex(((HKHubSchematicComponentPrivate)Component)->wirings, Loop);
        
        if (((CurrentWiring->slot[0] == SlotIndex) && (CurrentWiring->pin[0] == Pin)) || ((CurrentWiring->slot[1] == SlotIndex) && (CurrentWiring->pin[1] == Pin)))
        {
            CCArrayRemoveElementAtIndex(((HKHubSchematicComponentPrivate)Component)->wirings, Loop);
            break;
        }
    }
}

static inline void HKHubSchematicComponentSetWiring(CCComponent Component, HKHubSchematicWiring Wiring)
{
    CCAssertLog((Wiring.slot[0] < HK_HUB_SCHEMATIC_SLOT_MAX) && (Wiring.slot[1] < HK_HUB_SCHEMATIC_SLOT_MAX), "Wiring slots must be less than HK_HUB_SCHEMATIC_SLOT_MAX");
    CCAssertLog((Wiring.pin[0] < HK_HUB_SCHEMATIC_SLOT_PIN_MAX) && (Wiring.pin[1] < HK_HUB_SCHEMATIC_SLOT_PIN_MAX), "Wiring pins must be less than HK_HUB_SCHEMATIC_SLOT_PIN_MAX");
    CCAssertLog(Wiring.slot[0] != Wiring.slot[1], "Wiring slots must not be the same");
    
    size_t RemoveIndex = SIZE_MAX;
    _Bool Replaced = FALSE;
    
    for (size_t Loop = 0, Count = CCArrayGetCount(((HKHubSchematicComponentPrivate)Component)->wirings); Loop < Count; Loop++)
    {
        HKHubSchematicWiring *CurrentWiring = CCArrayGetElementAtIndex(((HKHubSchematicComponentPrivate)Component)->wirings, Loop);
        
        if (((CurrentWiring->slot[0] == Wiring.slot[0]) && (CurrentWiring->pin[0] == Wiring.pin[0])) || ((CurrentWiring->slot[1] == Wiring.slot[0]) && (CurrentWiring->pin[1] == Wiring.pin[0])) ||
            ((CurrentWiring->slot[0] == Wiring.slot[1]) && (CurrentWiring->pin[0] == Wiring.pin[1])) || ((CurrentWiring->slot[1] == Wiring.slot[1]) && (CurrentWiring->pin[1] == Wiring.pin[1])))
        {
            if (!Replaced)
            {
                *CurrentWiring = Wiring;
                Replaced = TRUE;
            }
            
            else RemoveIndex = Loop;
        }
    }
    
    if (!Replaced) CCArrayAppendElement(((HKHubSchematicComponentPrivate)Component)->wirings, &Wiring);
    else if (RemoveIndex != SIZE_MAX) CCArrayRemoveElementAtIndex(((HKHubSchematicComponentPrivate)Component)->wirings, RemoveIndex);
}

static inline CCEntity HKHubSchematicComponentGetSlot(CCComponent Component, uint8_t Index)
{
    CCAssertLog(Index < HK_HUB_SCHEMATIC_SLOT_MAX, "Index must be less than HK_HUB_SCHEMATIC_SLOT_MAX");
    
    return ((HKHubSchematicComponentPrivate)Component)->slots[Index];
}

static inline void HKHubSchematicComponentSetSlot(CCComponent Component, CCEntity Device, uint8_t Index)
{
    CCAssertLog(Index < HK_HUB_SCHEMATIC_SLOT_MAX, "Index must be less than HK_HUB_SCHEMATIC_SLOT_MAX");
    
    if (((HKHubSchematicComponentPrivate)Component)->slots[Index]) CCEntityDestroy(((HKHubSchematicComponentPrivate)Component)->slots[Index]);
    
    ((HKHubSchematicComponentPrivate)Component)->slots[Index] = Device;
}

#endif
