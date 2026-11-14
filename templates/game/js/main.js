// {{PROJECT}} 主脚本（ES module 占位）。
// 复刻时在此实现游戏循环与交互，过程证据留到 evidence/。

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

function drawPlaceholder() {
  ctx.fillStyle = "#14201c";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#9fb3aa";
  ctx.font = "16px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("{{PROJECT}}", canvas.width / 2, canvas.height / 2);
}

drawPlaceholder();
