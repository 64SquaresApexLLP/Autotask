/**
 * Centralized utility for parsing two-tier resolutions:
 * 1. Subscriber Self-Service Resolution (Customer Guidance - safe, jargon-free)
 * 2. Technician Field Remediation Protocol (Technical engineering steps, optical targets, tools)
 * 3. Mandatory Safety Precautions (ANSI Class 1M Laser, 90V POTS, electrical, thermal)
 */

export const parseResolutionContent = (resolution) => {
  if (!resolution) {
    return { subscriber: '', technician: '', safety: '' };
  }

  const raw = String(resolution).trim();

  // Pattern matching for modern structured two-tier resolutions
  const subMatch = raw.match(
    /###\s*(?:👤\s*)?SUBSCRIBER[^\n]*\n([\s\S]*?)(?=(?:###\s*(?:🔧\s*)?TECHNICIAN|⚠️?\s*SAFETY PRECAUTIONS|$))/i
  );
  const techMatch = raw.match(
    /###\s*(?:🔧\s*)?TECHNICIAN[^\n]*\n([\s\S]*?)(?=(?:⚠️?\s*SAFETY PRECAUTIONS|$))/i
  );
  const safetyMatch = raw.match(
    /(?:⚠️?\s*SAFETY PRECAUTIONS:?)\s*([\s\S]*)$/i
  );

  let subscriber = subMatch ? subMatch[1].trim() : '';
  let technician = techMatch ? techMatch[1].trim() : '';
  let safety = safetyMatch ? safetyMatch[1].trim() : '';

  // Fallback for legacy tickets or single-block resolutions
  if (!subscriber && !technician) {
    const safetyIdx = raw.search(/⚠️?\s*SAFETY PRECAUTIONS:?/i);
    const steps = safetyIdx !== -1 ? raw.substring(0, safetyIdx).trim() : raw.trim();
    if (!safety && safetyIdx !== -1) {
      safety = raw.substring(safetyIdx).replace(/^⚠️?\s*SAFETY PRECAUTIONS:?\s*/i, '').trim();
    }
    technician = steps;
    subscriber = [
      "1. Safe Physical Check: Verify that power adapters and network cables are plugged securely into their outlets.",
      "2. 30-Second Power Cycle: Disconnect power from the wall, wait 30 seconds, and reconnect. Allow 2-3 minutes for indicator lights to stabilize.",
      "3. Safety Advisory: Do not touch or bend green fiber optic cables or look directly into optical ports.",
      "4. Field Dispatch: A certified technician has been notified and will verify connectivity if service is not restored."
    ].join('\n');
  }

  // Remove any redundant header repetitions inside the extracted texts
  if (subscriber) {
    subscriber = subscriber.replace(/^###\s*(?:👤\s*)?SUBSCRIBER[^\n]*\n/i, '').trim();
  }
  if (technician) {
    technician = technician.replace(/^###\s*(?:🔧\s*)?TECHNICIAN[^\n]*\n/i, '').trim();
  }
  if (safety) {
    safety = safety.replace(/^⚠️?\s*SAFETY PRECAUTIONS:?\s*/i, '').trim();
  }

  return { subscriber, technician, safety };
};
