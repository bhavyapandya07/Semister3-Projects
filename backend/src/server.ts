import { app } from "./app";
import { connectDB } from "./db";

const port = Number(process.env.PORT ?? 5000);
connectDB().then(() => {
  app.listen(port, () => console.info(`[server] listening on :${port}`));
}).catch((err: unknown) => {
  console.error("[db] connection failed", err);
  process.exitCode = 1;
});
