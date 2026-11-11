# 帮我把 Clash 配成「国内直连、其余全走海外、断了也不漏」

你是在我这台电脑上动手配置网络的 agent。下面是要做到的样子、做法和检测方法，照着一步一步做，每一步达到完成标准再往下。

## 要做到的样子

最后逐条实测给我看：

1. 国内域名和国内 IP 直连，其余所有流量都走一个叫「海外出口」的策略组，组里没有 DIRECT。
2. TUN 开着，终端里的命令行程序（Claude Code、curl、git）和浏览器走同一个出口。
3. 海外节点断了，claude.ai 打不开，不会改走本地网络，国内网站照常能上。
4. Clash 崩了、被退出、TUN 消失，系统防火墙拦住普通程序，不让流量从网卡直接出去。
5. DNS 查询都进 Clash，替我解析海外域名的是海外的 DNS 服务器。

## 规矩

- 先备份。备份做完、还原脚本写好之前，不改任何配置。
- 订阅文件本身不动，所有改动放在客户端的扩展或覆写功能里。这样订阅更新不会冲掉改动。
- 改 Clash Verge 的文件之前先退出它，改完再打开。它运行时会把内存里的配置写回磁盘，开着改，改动会被冲掉。
- 要管理员权限的步骤，写成一个脚本文件，让我自己在「终端」应用里用 `sudo sh 脚本路径` 运行，密码我自己输。不要问我要密码，也不要用 `sudo -S` 或管道代输。
- 所有检测都绕开代理环境变量，直接测 TUN。每条 curl 都在 `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME="$HOME"` 下运行，并加 `--noproxy '*'`。不这样做，测的是代理端口，不是 TUN。
- 你自己的网络很可能也走这个出口。凡是会让海外网络断掉的操作（重启 Clash、三个演练），都写成一个脚本一次跑完，结尾自动恢复（用 `trap` 兜住异常退出），中间不要停下来等别的。
- 汇报只写实测到的结果，没测的写「没测」。

## 适用范围

下面的具体做法针对 macOS 上的 Clash Verge Rev 2.x：应用名 Clash Verge，菜单栏图标是猫，内核是 mihomo。

- 我用的是 Mihomo Party 或 Sparkle：它们也支持 JavaScript 全局覆写，同样的 `main(config)` 脚本可以照用。目录、重启方式、控制接口自己查清楚再改。
- 我用的是 ClashX 或别的不支持脚本覆写的客户端，或者我在 Windows 上：先告诉我。照「运行时配置」一节的目标手工迁移；断网开关只写了 macOS 的做法，做不到的项，在汇报里写明没做。

下文用这几个名字：

- `CV`：Verge 的配置目录，`$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev`。
- `APP`：Verge 应用路径，`/Applications/Clash Verge.app` 或 `$HOME/Applications/Clash Verge.app`。以正在运行的进程为准：`ps -axo command | grep 'MacOS/clash-verge$'`。
- `SOCK`：mihomo 控制接口的 unix socket。看核心进程 `verge-mihomo` 命令行里 `-ext-ctl-unix` 后面的路径，一般是 `/tmp/verge/verge-mihomo.sock`。
- 调接口：`curl -s --unix-socket "$SOCK" http://localhost/configs`。走 unix socket 不需要 secret。同一个 socket 路径可能被别的 mihomo 抢过，`/configs` 里的 `mixed-port` 等于 `verge.yaml` 的 `verge_mixed_port`，才是 Verge 的核心。

## 第 1 步：体检（只读）

查清楚并记下：

- macOS 版本，Verge 版本（`defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString`），界面和核心进程在不在、核心以哪个用户运行（root 说明在服务模式下运行）。
- 服务模式装没装：`/Library/LaunchDaemons/io.github.clash-verge-rev.clash-verge-rev.service.plist` 在不在。开 TUN 必须装。
- `CV/verge.yaml` 里的 `enable_tun_mode`、`enable_dns_settings`（DNS 覆写）、`enable_system_proxy`、`verge_mixed_port`。
- `CV/profiles/Script.js`（全局扩展脚本）是不是默认模板，也就是只有 `function main(config, profileName) { return config; }`。
- 当前订阅自己的扩展配置：`CV/profiles/` 下开头注释写着 `Profile Enhancement ... Template` 的小文件（规则、节点、策略组、Merge），以及小的 `.js` 文件。不是空模板的要告诉我，它们会在全局扩展之后生效。
- 系统首选 DNS：`scutil --dns | sed -n '/resolver #1/,/^$/p'`。首选是 `100.100.100.100` 的，说明 Tailscale 接管了系统 DNS，DNS 查询会绕过 Clash。
- 其他代理程序（别的 mihomo、clash、sing-box、xray 进程），开 TUN 后它们的流量也会被接管，告诉我。
- 节点和测速：从 `GET /proxies` 里取出真节点。跳过这几类：带 `all` 字段的策略组；`type` 是 Direct、Reject、RejectDrop、Pass、Compatible、Dns 的内置出站；名字里有「剩余、流量、到期、过期、套餐、官网、网址、订阅、重置、客服、公告、软件、教程、说明、频道、群组、续费、维护、无法、看到、不可用、旧线路、新线路、expire、traffic、reset、website」或像域名（含 `.com`、`.cn`、`.net` 这类）的信息条目。逐个调 `GET /proxies/<URL 编码后的节点名>/delay?timeout=5000&url=https%3A%2F%2Fwww.gstatic.com%2Fgenerate_204`，可以并发。

完成标准：上面每一项都有结果，能通的节点按延迟列出来，并标出哪些在香港、澳门、大陆。claude.ai 在这三个地区不提供服务，这些节点只能当链式代理的第一跳，不能当出口。

## 第 2 步：一次问完我这几件事

1. **出口用哪种。**
   - **A 直接出口**：我自己的 VPS 或专线本身就干净，或者直接用梯子里的某个海外节点，就把它直接当出口，不套链式代理。
   - **B 链式代理**：我单买了静态住宅 SOCKS5（商家给的 IP、端口、账号、密码四样），国内直连不上它，所以用梯子节点当第一跳，住宅 IP 当最终出口。

   我说不清的话，就问我是不是单独买了静态 IP。没买就是 A。A 让我从能通的节点里挑一个出口；B 要那四样信息，再挑一个第一跳（香港节点也可以）。
2. **确认会改的东西**：Verge 的全局扩展脚本（对所有订阅生效，原来的策略组会被「海外出口」取代）、开 TUN、关 DNS 覆写、装 Verge 服务模式、装 pf 断网开关（Clash 不在时，整台电脑除了局域网全部断网）、下载两份国内白名单。原配置先完整备份，随时一条命令还原。
3. 第 1 步发现 Tailscale 接管了 DNS 时，问我使用期间能不能关掉 Tailscale 的「Use Tailscale DNS」。关掉后 Tailscale 内网的机器名解析不了，用 IP 照常能连；还原时会改回去。

完成标准：我明确同意，并给了出口类型和节点（B 还有四样信息）。

## 第 3 步：完整备份，写好还原脚本

1. 建备份目录 `B="$HOME/clash-guard-backup/$(date +%Y%m%d-%H%M%S)"`，用 `ditto "$CV" "$B/verge"` 复制整个配置目录。
2. 生成校验清单，比对复制得对不对。`logs/` 不算配置，不比；`cache.db` 运行中会变，可以不同。

   ```bash
   (cd "$B/verge" && find . -type f ! -path './logs/*' -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) > "$B/manifest.txt"
   (cd "$CV" && find . -type f ! -path './logs/*' -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) | diff - "$B/manifest.txt"
   ```

3. 记下系统状态，存进 `$B/state.txt`：
   - 服务模式装没装；
   - `verge.yaml` 那四个值；
   - Verge 在不在运行；
   - 每个网络服务的 DNS：`networksetup -listallnetworkservices` 的每一项，跑 `networksetup -getdnsservers "服务名"`；
   - `scutil --proxy` 的输出；
   - `/tmp/verge` 的权限和属主：`stat -f '%Lp %Su %Sg' /tmp/verge`；
   - Tailscale 的 `CorpDNS`：`/Applications/Tailscale.app/Contents/MacOS/Tailscale debug prefs` 里的这个值。
4. 按下面的模板写 `$B/restore.sh`，把开头的变量换成实际值，DNS 那几行按 `state.txt` 逐个网络服务写。备份时为空的写 `empty`，可以写成 `networksetup -setdnsservers "Wi-Fi" empty`。

```sh
#!/bin/sh
# 还原到备份时的样子：sudo sh "这个文件的路径"。断网时也能用，不依赖 agent。
B="备份目录"; U="用户名"; UID_="用户 uid"; CV="配置目录"; APP="Verge 应用路径"
PORT=7897                # verge.yaml 的 verge_mixed_port
SERVICE_BEFORE=no        # 备份时服务模式装了没有：yes/no
VERGE_RUNNING=yes        # 备份时 Verge 在不在运行
TAILSCALE_DNS_BEFORE=none  # true/false/none（没装 Tailscale）
TMP_VERGE="750 用户名 wheel"  # /tmp/verge 原来的权限、属主、属组
[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行"; exit 1; }
[ -f "/Library/Application Support/clash-guard/off.sh" ] && sh "/Library/Application Support/clash-guard/off.sh"
launchctl asuser "$UID_" sudo -u "$U" osascript -e 'quit app "Clash Verge"' 2>/dev/null
i=0; while pgrep -f 'MacOS/clash-verge$' >/dev/null && [ $i -lt 30 ]; do sleep 1; i=$((i+1)); done
pkill -f 'MacOS/clash-verge$' 2>/dev/null
if [ "$SERVICE_BEFORE" = no ] && [ -f /Library/LaunchDaemons/io.github.clash-verge-rev.clash-verge-rev.service.plist ]; then
  "$APP/Contents/Resources/resources/clash-verge-service-uninstall"
  # 卸载程序不清这几样：服务的日志目录、锁文件、root 核心留下的 socket。不删的话，和装服务之前不一样
  rm -rf "$CV/logs/service" /tmp/verge/clash-verge-service.* /tmp/verge/verge-mihomo.sock
fi
pkill -f 'clash-verge-rev.clash-verge-rev/clash-verge.yaml' 2>/dev/null; sleep 2
rsync -a --delete --exclude=/logs/ "$B/verge/" "$CV/"
(cd "$CV" && find . -type f ! -path './logs/*' -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256) | diff -q - "$B/manifest.txt" >/dev/null \
  && echo "配置目录：与备份逐字节一致" || echo "配置目录：和备份不一致！"
networksetup -setdnsservers "Wi-Fi" empty   # 每个网络服务一行，改回备份时的值
if [ "$TAILSCALE_DNS_BEFORE" != none ]; then
  sudo -u "$U" /Applications/Tailscale.app/Contents/MacOS/Tailscale set --accept-dns="$TAILSCALE_DNS_BEFORE"
fi
set -- $TMP_VERGE; [ -d /tmp/verge ] && chown "$2:$3" /tmp/verge && chmod "$1" /tmp/verge
# 刚卸掉的 root 核心可能还占着代理端口，等它放开再打开 Verge，否则新核心抢不到端口，系统代理指向一个空端口
i=0; while lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1 && [ $i -lt 30 ]; do sleep 1; i=$((i+1)); done
if [ "$VERGE_RUNNING" = yes ]; then
  launchctl asuser "$UID_" sudo -u "$U" open "$APP"
  SOCK=/tmp/verge/verge-mihomo.sock; i=0
  until sudo -u "$U" curl -s --unix-socket "$SOCK" http://localhost/configs 2>/dev/null | grep -q "\"mixed-port\":$PORT"; do
    i=$((i+1))
    [ $i = 30 ] && sudo -u "$U" curl -s --unix-socket "$SOCK" -X PUT 'http://localhost/configs?force=true' \
      -H 'Content-Type: application/json' --data "{\"path\":\"$CV/clash-verge.yaml\"}" >/dev/null
    [ $i -gt 60 ] && { echo "Verge 的代理端口 $PORT 没起来：在 Verge 设置里重启一次内核"; break; }
    sleep 1
  done
fi
echo "还原完成。Verge 启动时会重新生成 clash-verge.yaml 等运行时文件，键的顺序会变，内容和原来一样。"
```

完成标准：清单比对除 `cache.db` 外没有差异，`restore.sh` 写好，把它的完整运行命令告诉我。

## 第 4 步：写配置（这一步不需要管理员权限）

1. **先下载两份国内白名单**，放进 `CV/ruleset/`。用的是 Loyalsoldier/clash-rules，每天更新：
   - `direct.txt`（国内域名，11 万条左右）存为 `cg-cn-domain.yaml`；
   - `cncidr.txt`（国内 IP 段）存为 `cg-cn-cidr.yaml`。

   地址是 `https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/文件名`。先经 Verge 现在的代理端口下（`curl -sL -x http://127.0.0.1:端口`），下不动再试 `https://testingcf.jsdelivr.net/gh/Loyalsoldier/clash-rules@release/文件名`。下载后检查：文件以 `payload:` 开头，域名文件超过 1 万行，IP 文件超过 1000 行。核心之后会经海外出口每天自动更新它们。
2. **写全局扩展脚本** `CV/profiles/Script.js`，用下面的模板，只改最上面 `CG` 的三个值。
   - 原来的 Script.js 不是默认模板，就把它整个保留到文件末尾，把其中的 `function main(` 改名为 `function clashGuardUserMain(`，再把模板最后的 `main` 改成 `return clashGuard(clashGuardUserMain(config, profileName));`。
   - 原脚本里找不到 `function main(`，就先停下来问我。
3. **改 Verge 自己的两个开关**，各只改一行，没有这一行就加上：
   - `CV/verge.yaml`：`enable_dns_settings: false`。Verge 的「DNS 覆写」会盖掉脚本里的 DNS 设置。
   - `CV/config.yaml`：`ipv6: false`（Verge 设置页的「IPv6」开关）。开着 TUN 时，Verge 会用这个开关重写 DNS 的 `ipv6`，盖掉脚本里的 `ipv6: false`。

   TUN 开关留到第 5 步，装好服务模式后再开。
4. **重启 Verge，写成一个脚本一次跑完**：
   1. `osascript -e 'quit app "Clash Verge"'`，等 `MacOS/clash-verge` 进程消失；
   2. 结束以你的身份运行、还没退出的核心：`pkill -u "$(id -u)" -f 'clash-verge-rev.clash-verge-rev/clash-verge.yaml'`；
   3. 写入第 2、3 项的文件；
   4. `open "$APP"`；
   5. 等到 `/configs` 返回的 `mixed-port` 等于 `verge_mixed_port`。

   刚重启时上一个核心可能还占着端口，`mixed-port` 会显示 0，Verge 通常 30 秒内会自己重载。超过 60 秒还是 0，就调一次 `PUT /configs?force=true`，请求体是 `{"path":"CV/clash-verge.yaml 的完整路径"}`。

5. 我同意关掉 Tailscale 的「Use Tailscale DNS」的话，现在运行 `/Applications/Tailscale.app/Contents/MacOS/Tailscale set --accept-dns=false`，不需要 sudo。

```js
// >>> clash-guard >>>
// 国内白名单直连，其余全部走「海外出口」，组里没有 DIRECT。还原：sudo sh "备份目录/restore.sh"
var CG = {
  mode: "direct",            // direct：节点直接当出口；chain：住宅 SOCKS5 经「跳板」链式出去
  preferred: ["节点名"],      // direct 填出口节点；chain 填第一跳节点
  residential: null          // chain 时填 { server: "1.2.3.4", port: 1080, username: "账号", password: "密码" }
};
function clashGuard(config) {
  var EXIT = "海外出口", HOP = "跳板", RES = "住宅出口", DRILL = "⛔ 断网演练";
  var info = /剩余|流量|到期|过期|套餐|官网|网址|订阅|重置|客服|公告|软件|教程|说明|频道|群组|续费|维护|无法|看到|不可用|旧线路|新线路|expire|traffic|reset|website|[a-z0-9-]+\.(com|cn|net|org|xyz|top|me|io|cc|site|club|vip|pro|app|link|info)/i;
  var region = /香港|澳门|中国|大陆|回国|国内|hong ?kong|maca[uo]|🇭🇰|🇲🇴|🇨🇳|(^|[^a-z])(hk|mo)([^a-z]|$)/i;
  var builtin = /^(direct|reject|rejectdrop|reject-drop|pass|compatible|dns)$/i;
  var proxies = (config.proxies || []).filter(function (p) { return p && p.name !== DRILL && p.name !== RES; });
  var nodes = proxies.filter(function (p) { return !builtin.test(String(p.type || "")) && !info.test(String(p.name)); })
                     .map(function (p) { return p.name; });
  var providers = Object.keys(config["proxy-providers"] || {});
  function ordered(list) {
    var pref = CG.preferred.filter(function (n) { return list.indexOf(n) >= 0; });
    return pref.concat(list.filter(function (n) { return pref.indexOf(n) < 0; }));
  }
  function group(name, members, exclude) {
    var g = { name: name, type: "select", proxies: members };
    if (providers.length) { g.use = providers; g["exclude-filter"] = exclude; g["exclude-type"] = "Direct|Reject|RejectDrop|Pass|Compatible|Dns"; }
    return g;
  }
  var groups, drill = { name: DRILL, type: "socks5", server: "192.0.2.1", port: 9, udp: true };
  if (CG.mode === "chain") {
    var r = CG.residential;
    var res = { name: RES, type: "socks5", server: r.server, port: r.port, udp: false, "dialer-proxy": HOP };
    if (r.username) { res.username = r.username; res.password = r.password; }
    proxies.push(res);
    groups = [{ name: EXIT, type: "select", proxies: [RES, DRILL] },
              group(HOP, ordered(nodes), "(?i)" + info.source)];
  } else {
    var exits = nodes.filter(function (n) { return !region.test(n); });
    groups = [group(EXIT, ordered(exits).concat([DRILL]), "(?i)" + info.source + "|" + region.source)];
  }
  proxies.push(drill);

  var rules = [];
  ["claude.ai", "claude.com", "anthropic.com", "claudeusercontent.com", "claudemcpclient.com"].forEach(function (d) {
    rules.push("DOMAIN-SUFFIX," + d + "," + EXIT);
  });
  if (CG.mode === "chain") {
    var h = CG.residential.server;
    rules.push(/^[0-9.]+$/.test(h) ? "IP-CIDR," + h + "/32," + HOP + ",no-resolve" : "DOMAIN," + h + "," + HOP);
  }
  ["IP-CIDR,127.0.0.0/8", "IP-CIDR,10.0.0.0/8", "IP-CIDR,172.16.0.0/12", "IP-CIDR,192.168.0.0/16",
   "IP-CIDR,169.254.0.0/16", "IP-CIDR,100.64.0.0/10", "IP-CIDR,224.0.0.0/4",
   "IP-CIDR6,::1/128", "IP-CIDR6,fc00::/7", "IP-CIDR6,fe80::/10"].forEach(function (x) { rules.push(x + ",DIRECT,no-resolve"); });
  ["GEOSITE,private", "GEOSITE,bilibili", "DOMAIN-KEYWORD,mirrorakam", "DOMAIN-SUFFIX,bilibili.com", "DOMAIN-SUFFIX,hdslb.com",
   "DOMAIN-SUFFIX,bilivideo.com", "DOMAIN-SUFFIX,bilivideo.cn", "DOMAIN-SUFFIX,biliapi.net", "DOMAIN-SUFFIX,biliapi.com",
   "DOMAIN-SUFFIX,weixin.com", "DOMAIN-SUFFIX,wechat.com"].forEach(function (x) { rules.push(x + ",DIRECT"); });
  rules.push("GEOSITE,geolocation-!cn," + EXIT,
             "RULE-SET,cg-cn-domain,DIRECT", "GEOSITE,cn,DIRECT",
             "RULE-SET,cg-cn-cidr,DIRECT,no-resolve", "GEOIP,CN,DIRECT,no-resolve",
             "MATCH," + EXIT);

  var cn = ["223.5.5.5", "119.29.29.29"];
  var base = "https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/";
  config.proxies = proxies;
  config["proxy-groups"] = groups;
  config["rule-providers"] = {
    "cg-cn-domain": { type: "http", behavior: "domain", format: "yaml", url: base + "direct.txt",
                      path: "./ruleset/cg-cn-domain.yaml", interval: 86400, proxy: EXIT },
    "cg-cn-cidr": { type: "http", behavior: "ipcidr", format: "yaml", url: base + "cncidr.txt",
                    path: "./ruleset/cg-cn-cidr.yaml", interval: 86400, proxy: EXIT }
  };
  config.rules = rules;
  delete config["sub-rules"];
  config.dns = {
    enable: true, ipv6: false, "enhanced-mode": "fake-ip", "fake-ip-range": "198.18.0.1/16",
    "fake-ip-filter": ["*.lan", "*.local", "*.arpa", "time.*.com", "ntp.*.com", "+.msftconnecttest.com", "+.msftncsi.com", "localhost.ptlogin2.qq.com"],
    "use-hosts": true, "use-system-hosts": true, "respect-rules": true,
    "default-nameserver": cn, "proxy-server-nameserver": cn, "direct-nameserver": cn,
    nameserver: ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"]
  };
  config.sniffer = {
    enable: true, "force-dns-mapping": true, "parse-pure-ip": true, "override-destination": true,
    sniff: { HTTP: { ports: [80, "8080-8880"] }, TLS: { ports: [443, 8443] }, QUIC: { ports: [443, 8443] } },
    "skip-domain": ["+.push.apple.com"]
  };
  return config;
}
// <<< clash-guard <<<
function main(config, profileName) {
  return clashGuard(config);
}
```

完成标准：Verge 重新打开后，`GET /proxies` 里有「海外出口」组，B 类还有「跳板」组。`GET /rules` 的最后一条是 `Match` 指向「海外出口」，代理端口在监听。没有「海外出口」组，说明脚本报错没生效：看 Verge 日志，修好再往下。修不好就停下来，让我跑还原。

## 第 5 步：装服务模式和断网开关（我来运行）

按下面的模板写 `$HOME/clash-guard/apply-root.sh`，换掉开头的变量，然后把运行命令发给我：`sudo sh "$HOME/clash-guard/apply-root.sh"`。

我运行期间 Verge 会重启一次，海外网络断几十秒，你等我回复。它会：

1. 装服务模式（TUN 需要 root）；
2. 退出 Verge，把 `verge.yaml` 的 `enable_tun_mode` 改成 true，再打开 Verge；
3. 等 TUN 网卡出现；
4. 等到 TUN 真的起来了，才装断网开关。TUN 不在时装上，整台电脑会立刻断网。

```sh
#!/bin/sh
# 装 Verge 服务模式和 pf 断网开关：sudo sh "这个文件的路径"
U="用户名"; UID_="用户 uid"; APP="Verge 应用路径"; CV="配置目录"; TUN="utun1024"   # TUN 网卡名：CV/config.yaml 里 tun 下的 device
D="/Library/Application Support/clash-guard"; PLIST=/Library/LaunchDaemons/com.clash-guard.killswitch.plist
[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行"; exit 1; }
if [ ! -f /Library/LaunchDaemons/io.github.clash-verge-rev.clash-verge-rev.service.plist ]; then
  echo "安装 Clash Verge 服务模式……"; "$APP/Contents/Resources/resources/clash-verge-service-install" || exit 1; sleep 3
fi
echo "重启 Clash Verge……"
launchctl asuser "$UID_" sudo -u "$U" osascript -e 'quit app "Clash Verge"'
i=0; while pgrep -f 'MacOS/clash-verge$' >/dev/null && [ $i -lt 30 ]; do sleep 1; i=$((i+1)); done
pkill -u "$U" -f 'clash-verge-rev.clash-verge-rev/clash-verge.yaml' 2>/dev/null; sleep 2
if grep -q '^enable_tun_mode:' "$CV/verge.yaml"; then
  sudo -u "$U" sed -i '' 's/^enable_tun_mode:.*/enable_tun_mode: true/' "$CV/verge.yaml"
else
  sudo -u "$U" sh -c "echo 'enable_tun_mode: true' >> '$CV/verge.yaml'"
fi
launchctl asuser "$UID_" sudo -u "$U" open "$APP"
echo "等 TUN 网卡 $TUN ……"
i=0; until ifconfig "$TUN" >/dev/null 2>&1; do i=$((i+1)); [ $i -gt 120 ] && { echo "TUN 两分钟没起来，断网开关没装。把这段输出发给 agent。"; exit 1; }; sleep 1; done
pfctl -s rules 2>/dev/null | grep -qF 'anchor "com.apple/*"' || { echo "系统 pf 主规则里没有 com.apple 锚点，断网开关挂上去也不生效，没装。把这段输出发给 agent。"; exit 1; }
echo "TUN 已起来，安装断网开关……"
mkdir -p "$D"
cat > "$D/pf.rules" <<EOF
# clash-guard 断网开关：普通程序的流量只能进 Clash 的 TUN 或发往局域网；root 进程（Clash 核心）不受限
table <cg_local> const { 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.168.0.0/16 224.0.0.0/4 255.255.255.255/32 ::1/128 fc00::/7 fe80::/10 ff00::/8 }
pass out quick on lo0 all no state label "clash-guard"
pass out quick on $TUN all no state label "clash-guard"
block drop out quick proto { tcp udp } from any to ! <cg_local> user != 0 label "clash-guard"
EOF
cat > "$D/keeper.sh" <<'EOF'
#!/bin/sh
# 每分钟确认 pf 开着、断网规则在（重启后、或别的程序重载 pf 后自动补回）
D="/Library/Application Support/clash-guard"
[ -f "$D/pf.rules" ] || exit 0
/sbin/pfctl -s info 2>/dev/null | /usr/bin/grep -q "Status: Enabled" || /sbin/pfctl -E 2>&1 | /usr/bin/sed -n 's/^Token : //p' > "$D/pf.token"
/sbin/pfctl -a com.apple/clash-guard -s rules 2>/dev/null | /usr/bin/grep -q clash-guard || /sbin/pfctl -a com.apple/clash-guard -f "$D/pf.rules" >/dev/null 2>&1
exit 0
EOF
cat > "$D/off.sh" <<'EOF'
#!/bin/sh
# 一键解除断网开关：sudo sh "/Library/Application Support/clash-guard/off.sh"
D="/Library/Application Support/clash-guard"
/bin/launchctl bootout system/com.clash-guard.killswitch 2>/dev/null
/sbin/pfctl -a com.apple/clash-guard -F all 2>/dev/null
T=$(cat "$D/pf.token" 2>/dev/null); [ -n "$T" ] && /sbin/pfctl -X "$T" 2>/dev/null
/bin/rm -f /Library/LaunchDaemons/com.clash-guard.killswitch.plist; /bin/rm -rf "$D"
echo "断网开关已解除"
EOF
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.clash-guard.killswitch</string>
<key>ProgramArguments</key><array><string>/bin/sh</string><string>$D/keeper.sh</string></array>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>60</integer>
</dict></plist>
EOF
chmod 644 "$PLIST" "$D/pf.rules"; chmod 755 "$D/keeper.sh" "$D/off.sh"
pfctl -n -f "$D/pf.rules" 2>/dev/null || { echo "pf 规则校验失败"; exit 1; }
launchctl bootout system/com.clash-guard.killswitch 2>/dev/null; launchctl bootstrap system "$PLIST"; sleep 3
pfctl -s info 2>/dev/null | head -1; pfctl -a com.apple/clash-guard -s rules 2>/dev/null
echo "完成。只解除断网开关：sudo sh \"$D/off.sh\""
```

完成标准：我贴回的输出里有 `Status: Enabled` 和四条 `label "clash-guard"` 规则（`proto { tcp udp }` 那条会展开成两条）。之后由你确认：

- 核心以 root 运行，`/configs` 里 `tun.enable` 为 true；
- 「海外出口」（B 类是「跳板」）选中的是我挑的节点，不是就用 `PUT /proxies/<组名>` 和 `{"name":"节点名"}` 选回来；
- 调 `PUT /providers/rules/cg-cn-domain` 和 `PUT /providers/rules/cg-cn-cidr` 刷新白名单，`GET /providers/rules` 里两份都有几千条以上。

## 第 6 步：检测（不加 sudo）

不加 sudo 是因为 root 的流量不受断网开关限制，测出来不准。第 5 步刚跑完的十几秒里 TUN 和 DNS 还在建立，头几个请求可能超时，先等 10 秒再测。

写一个检测脚本一次跑完。先在后台录 Clash 日志：`curl -sN --unix-socket "$SOCK" 'http://localhost/logs?level=info' > /tmp/cg-log.txt &`。跑完下面的请求再停掉它，从日志里 grep `--> 域名:端口 match 规则 using 出口` 这一行，它是每个请求实际走了哪条规则、哪个出口的证据。

| 检测 | 做法 | 通过的样子 |
|---|---|---|
| 运行模式 | `GET /configs`；`CV/clash-verge.yaml`（Verge 生成的运行时配置） | `mode` 是 `rule`（全局模式会走 GLOBAL 组，那里面有 DIRECT），`tun.enable` 为 true，`ifconfig <tun.device>` 存在；`clash-verge.yaml` 的 `dns:` 下 `ipv6: false` |
| 兜底和直连规则 | `GET /rules` | 最后一条 `Match` → 海外出口；所有指向 DIRECT 的规则，都是第 4 步模板里写的那些，没有多余的；没有规则指向「组里含 DIRECT」的组 |
| 出口组 | `GET /proxies` | 「海外出口」（B 类还有「跳板」）的 `all` 里没有 DIRECT，`now` 不是「⛔ 断网演练」 |
| 国内直连 | curl `https://www.baidu.com`、`https://www.bilibili.com`、`https://myip.ipip.net` | 都能打开；日志里是 `using DIRECT`；ipip 显示「来自于：中国……」，也就是我本地宽带的 IP |
| claude.ai 走海外 | curl `https://claude.ai/cdn-cgi/trace` | `loc=` 不是 CN、HK、MO；日志里是 `using 海外出口[节点名]` |
| Claude Code 的接口 | curl `https://api.anthropic.com/v1/messages` | 有 HTTP 状态码（没带 key，4xx 正常）；日志里走海外出口 |
| 终端出口 IP | curl `https://ipinfo.io/json` | `country` 在海外，`ip` 和 claude.ai 看到的一样；B 类的出口 IP 应该是住宅代理的出口 |
| DNS 进了 Clash | `dscacheutil -q host -a name "cg-$RANDOM$RANDOM.claude.ai"`（用随机子域名，避开系统 DNS 缓存） | `ip_address` 是 `198.18.x.x`（Clash 给的虚拟地址），没有 `ipv6_address` |
| 谁在替我解析 | curl `-L https://edns.ip-api.com/json` | `dns.geo` 不是中国 |

完成标准：每一项都通过。没通过的，按文末「故障速查」处理后重测。

## 第 7 步：三个演练（不加 sudo，每个写成一个脚本一次跑完）

每个演练开头先记下当前状态，用 `trap` 保证中途出错也会恢复。每个演练都要在恢复后再测一次 claude.ai，确认正常。

1. **海外节点挂了**：
   - 演练：`PUT /proxies/海外出口` 切到 `{"name":"⛔ 断网演练"}`（它指向 192.0.2.1，必然连不上），再 `DELETE /connections` 断掉旧连接，然后测 claude.ai、ipinfo、baidu。
   - 恢复：切回原来的节点。
   - 通过：claude.ai 和 ipinfo 连不上，日志里 claude.ai 是 `using 海外出口[⛔ 断网演练]`，没有 `using DIRECT`；baidu 照常。
2. **TUN 消失（模拟 Clash 崩溃）**：
   - 演练：`PATCH /configs`，请求体 `{"tun":{"enable":false}}`，等 TUN 网卡消失，然后测同样三个网址。再测两个直接写 IP、不用 DNS 的地址：`curl -sk https://1.1.1.1/cdn-cgi/trace` 和 `curl -sk https://223.5.5.5`，并记下 `route -n get 1.1.1.1` 里的 `interface`。
   - 恢复：`PATCH /configs`，请求体 `{"tun":{"enable":true}}`，等网卡回来。回不来就 `PUT /configs?force=true` 重载 `clash-verge.yaml`。
   - 通过：五个全部连不上，连 baidu 都打不开，而 `route` 显示当时走的是物理网卡（en0、en1 这类）。只测域名的话，连不上也可能只是 DNS 断了；直接写 IP 的也连不上，才说明是断网开关在拦。没有一个请求以国内 IP 成功出去。
3. **退出 Clash Verge**：
   - 演练：`osascript -e 'quit app "Clash Verge"'`，等界面进程消失，看核心和 TUN 还在不在（服务模式下核心可能不随界面退出），然后测同样三个网址。
   - 恢复：`open "$APP"`，等 TUN 和代理端口恢复。
   - 通过：claude.ai 和 ipinfo 要么连不上，要么仍然是海外 IP，绝不能出现国内 IP。

## 第 8 步：汇报

用一张表列出第 6 步每一项检测和第 7 步每个演练的结果，带上证据：出口 IP 和地区、国内 IP、DNS 服务器所在地、演练时每个网址的 HTTP 结果和日志里的出口。只写实测到的。

然后告诉我三条命令：

- 一键还原：`sudo sh "备份目录/restore.sh"`
- 只解除断网开关：`sudo sh "/Library/Application Support/clash-guard/off.sh"`
- 以后想复查：重跑第 6 步的检测脚本，告诉我它存在哪。

再提醒我这几件事：

- 换节点时，只在 Verge「代理」页的「海外出口」（B 类还有「跳板」）里选，别选「⛔ 断网演练」。
- 顶部模式保持「规则」。
- 微信这类保持长连接的程序要重启一次，旧连接才会走新路径。
- 所有节点都挂了时，订阅也更新不了，因为断网开关拦着直连。先用 `off.sh` 解除，更新订阅后再让你重装。
- root 身份运行的系统进程不受断网开关限制，因为 Clash 核心本身以 root 运行；Claude Code、浏览器这些普通程序都受限制。

## 已经配过，要换出口类型或换节点

- 只在 Verge 里换个节点：直接在「代理」页选，不用找你。
- 要在 A、B 两类之间切换，或者换住宅 IP：
  1. 沿用第一次的备份和 `restore.sh`，不要重新备份。现在的状态已经不是原样，重新备份会让还原回不到最初。
  2. 只改 `CV/profiles/Script.js` 开头 `CG` 的三个值。
  3. 照第 4 步第 4 项的方式重启 Verge，一次跑完。服务模式和断网开关已经在，不用再跑第 5 步。
  4. 重启后确认 TUN 在，再重做第 6、7 步。

## 运行时配置的道理（迁移到别的客户端时照这个做）

- **策略组**：「海外出口」是 select 类型。select 不会自己换节点，选中的节点挂了就是断网，这就是「不回落」。组里没有 DIRECT，也就没地方回落。B 类的「住宅出口」带 `dialer-proxy: 跳板`，经第一跳连出去，并设 `udp: false`：住宅 SOCKS5 经链式基本转不了 UDP，直接拒掉，浏览器会马上改用 TCP。
- **规则顺序就是优先级**：
  1. Claude 自家域名走海外出口。
  2. B 类的住宅入口地址走跳板。比特浏览器这类工具直连这个住宅 IP 时，要是被兜底规则送进住宅出口自己，就绕成了死循环。
  3. 局域网直连。
  4. B 站、微信补丁直连。B 站视频走 Akamai 的 `upos-*-mirrorakam.akamaized.net`，`DOMAIN-SUFFIX` 按标签匹配，写成 `mirrorakam.akamaized.net` 匹配不上，所以用 `DOMAIN-KEYWORD,mirrorakam`。
  5. `GEOSITE,geolocation-!cn` 走海外出口。下一条的国内名单里混着几百条海外公司在国内能直连的域名（googletagmanager、doubleclick、app-measurement……），Claude 的网页调用这些第三方时，就会用国内 IP 出去，所以先把它们拦到海外。
  6. 国内域名名单和内置 `GEOSITE,cn` 直连。
  7. 国内 IP 名单和内置 `GEOIP,CN` 直连。
  8. 其余全部走海外出口。

  IP 类规则都带 `no-resolve`，不为匹配 IP 规则去本地解析域名。
- **DNS**：
  - `fake-ip`：系统查任何域名，Clash 先回一个 198.18.x.x 的虚拟地址，真正的解析由出口节点在海外做。
  - 国内 DNS 只用于直连的国内域名（`direct-nameserver`）和节点服务器地址（`proxy-server-nameserver`）。
  - 其余查询走 1.1.1.1、8.8.8.8 的 DoH，`respect-rules` 让这些查询本身也经海外出口发出。
  - `ipv6: false`：不返回 IPv6 地址，程序就不会绕开 TUN 走 IPv6。Verge 开着 TUN 时会拿它设置页的「IPv6」开关重写这一项，所以那个开关也要关。
  - 嗅探：程序拿 IP 直连时，从 TLS 握手里读出域名，再按规则走。
  - TUN 开着时，Verge 会把当前网络服务的 DNS 改成 114.114.114.114。这个地址不在局域网里，查询包会被路由进 TUN，被 Clash 接管。
- **断网开关**：pf 规则挂在 `com.apple/clash-guard` 锚点下，不改 `/etc/pf.conf`。普通程序的 TCP/UDP 只能进 TUN 网卡或发往局域网；Clash 核心以 root 运行，不受限，由它替大家把流量发出去。TUN 一消失，普通程序除了局域网全部连不上，DNS 查询也发不出去。LaunchDaemon 每分钟检查一次，pf 被关、规则被清就补回来，重启后自动生效。

## 故障速查

| 现象 | 原因 | 处理 |
|---|---|---|
| DNS 那项失败，系统首选 DNS 是 100.100.100.100 | Tailscale 的「Use Tailscale DNS」接管了系统 DNS，查询走 Tailscale 自己的网卡 | 经我同意后运行 `/Applications/Tailscale.app/Contents/MacOS/Tailscale set --accept-dns=false`，还原脚本会改回去 |
| 首选 DNS 是 192.168.x.1 这类路由器地址 | Verge 没把系统 DNS 改成公网地址，查询走局域网，绕开 TUN | 重启 Verge；还不行，经我同意后给当前网络服务设一个公网 DNS，比如 223.5.5.5，并写进还原脚本 |
| `clash-verge.yaml` 的 `dns.ipv6` 是 true | Verge 设置页的「IPv6」开着，开 TUN 时它盖掉了脚本的设置 | 退出 Verge，把 `CV/config.yaml` 的 `ipv6` 改成 false，再打开 |
| 重启后 `mixed-port` 一直是 0 | 上一个核心还占着端口 | 等 30 秒；不行就 `PUT /configs?force=true` 重载 |
| TUN 起不来 | 服务模式没装好，核心不是 root | 看 `/Library/LaunchDaemons` 里有没有服务的 plist，重跑第 5 步 |
| 没有「海外出口」组 | 全局扩展脚本报错 | 看 Verge 的日志；脚本出错时 Verge 会退回订阅原样，这时整套保护都不在 |
| 直连规则里多出东西 | 订阅自己的扩展规则在全局扩展之后生效 | 告诉我是哪份，由我决定清不清 |
| 所有海外请求超时，国内正常 | 选中的节点挂了，这正是不回落 | 换节点；B 类先分别测「住宅出口」和「跳板」哪个不通 |
| 整台电脑上不了网 | Clash 没开或 TUN 没起来，断网开关在拦 | 打开 Verge；要先恢复上网就运行 `off.sh` |
