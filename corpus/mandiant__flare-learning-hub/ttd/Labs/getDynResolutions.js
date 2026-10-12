/**Copyright 2026 Google LLC
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *     https://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/// <reference path="JSProvider.d.ts" />

'use strict';

/**
 * Creates a function alias 'gdr' for getDynResolutions. Invoke using !gdr(@$startAddr, @$endAddr).
 */
function initializeScript() {
	return [new host.functionAlias(getDynResolutions, 'gdr')];
}

/**
 * Finds and prints dynamically resolved functions (GetProcAddress) and
 * loaded modules (LoadLibraryA/W) between a start and end address in a TTD trace.
 * @param {host.Int64} startAddr - The start address of the range to search.
 * @param {host.Int64} endAddr - The end address of the range to search.
 */
function getDynResolutions(startAddr, endAddr) {
  const printLog = host.diagnostics.debugLog;

  // Query for all calls to the specified functions within the address range.
  // Deduplicate calls via grouping by ReturnAddress
  const calls = host.currentSession.TTD.Calls('kernel32!GetProcAddress', 'kernel32!LoadLibrary*').Where(c => c.ReturnAddress > startAddr && c.ReturnAddress < endAddr).GroupBy(m => m.ReturnAddress).Select(n => n.First()).OrderBy(p => p.TimeStart);
  const is64Bit = host.namespace.Debugger.State.PseudoRegisters.General.ptrsize == 8;

  var lines = [];
  let i = 1;

  for (const call of calls) {
    try {
      // Set the debugger context to the time of the call.
      call.TimeStart.SeekTo();

      let namePointer = null;
      const functionName = call.Function;
      const regs = host.currentThread.Registers.User;

      // Manually get the argument pointer based on architecture and calling convention.
      if (is64Bit) {
        // x64 fastcall convention: 1st arg in RCX, 2nd in RDX.
        if (functionName.includes('GetProcAddress')) {
          namePointer = regs.rdx; // 2nd argument
        } else { // LoadLibraryA or LoadLibraryW
          namePointer = regs.rcx; // 1st argument
        }
      } else {
        // x86 stdcall convention: args are on the stack.
        const esp = regs.esp;
        let namePointerAddress;
        if (functionName.includes('GetProcAddress')) {
          // 2nd argument is at [esp + 8]
          namePointerAddress = esp.add(8);
        } else { // LoadLibraryA or LoadLibraryW
          // 1st argument is at [esp + 4]
          namePointerAddress = esp.add(4);
        }
        // Read the 4-byte pointer value from the stack address.
        namePointer = host.memory.readMemoryValues(namePointerAddress, 1, 4)[0];
      }

      if (!namePointer || namePointer.compareTo(0) === 0) {
          continue;
      }

      let resolvedName = '';
      let resolutionType = 'module';

      if (functionName.includes('LoadLibraryW')) {
        resolvedName = host.memory.readWideString(namePointer);
      } else { // GetProcAddress or LoadLibraryA
        resolvedName = host.memory.readString(namePointer);
        if (functionName.includes('GetProcAddress')) {
          resolutionType = 'function';
        }
      }

      const returnAddress = call.ReturnAddress.toString(16);
      lines.push(`${i}. Resolved ${resolutionType}: ${resolvedName} at address 0x${returnAddress}\r\n`);
      i++;
    } catch (e) {
      printLog(`Error processing call at ${call.TimeStart}: ${e}\n`);
    }
  }
  
  // Print results
  printLog("Found resolved modules and functions:\r\n");
  for (var line of lines) {
    printLog(line);
  }
}