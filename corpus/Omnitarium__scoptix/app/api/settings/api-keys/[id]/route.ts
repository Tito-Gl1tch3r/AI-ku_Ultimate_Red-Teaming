import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";

const patchSchema = z.object({
  label: z.string().min(1).max(120).optional(),
  proxyUrl: z.string().url().nullable().optional(),
  isDisabled: z.boolean().optional(),
});

export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const json = await req.json().catch(() => null);
  const parsed = patchSchema.safeParse(json);
  if (!parsed.success) return NextResponse.json({ error: "Invalid body" }, { status: 400 });

  const updated = await prisma.apiKey.update({
    where: { id },
    data: {
      ...(parsed.data.label ? { label: parsed.data.label } : {}),
      ...(parsed.data.proxyUrl !== undefined ? { proxyUrl: parsed.data.proxyUrl } : {}),
      ...(parsed.data.isDisabled !== undefined ? { isDisabled: parsed.data.isDisabled } : {}),
    },
  });
  return NextResponse.json({
    key: {
      id: updated.id,
      label: updated.label,
      provider: updated.provider,
      proxyUrl: updated.proxyUrl,
      isDisabled: updated.isDisabled,
    },
  });
}

export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  await prisma.apiKey.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}
