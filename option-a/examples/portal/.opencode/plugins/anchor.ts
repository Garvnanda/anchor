import { createAnchorPlugin } from "@anchor-ai/opencode";
import { createLocalServer } from "@anchor-ai/server";

export default {
  id: "anchor.local-portal",
  async setup(ctx) {
    const token = process.env.ANCHOR_PORTAL_TOKEN;
    if (!token) throw new Error("Set ANCHOR_PORTAL_TOKEN before starting the local portal");
    const portal = await createLocalServer({ port: 8080, token });
    try {
      const cleanup = await createAnchorPlugin(undefined, portal.publish).setup(ctx);
      return async () => {
        try {
          await cleanup?.();
        } finally {
          await portal.close();
        }
      };
    } catch (error) {
      await portal.close();
      throw error;
    }
  },
};
