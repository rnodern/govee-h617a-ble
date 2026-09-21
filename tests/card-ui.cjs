// Run with Node and Playwright available on NODE_PATH.
const {chromium} = require("playwright");
const assert = require("node:assert/strict");
const {pathToFileURL} = require("node:url");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({headless:true, channel:"chrome"});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844},hasTouch:true});
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(pathToFileURL(path.join(__dirname,"card-preview.html")).href);
    await page.getByRole("button",{name:"DIY",exact:true}).click();
    await page.locator(".segment").nth(0).tap();
    await page.locator("#fill").fill("#0000ff");
    await page.locator(".segment").nth(1).tap();
    assert.equal(await page.evaluate(() => window.calls.length),0);
    await page.getByRole("button",{name:"Breathe",exact:true}).click();
    await page.locator("#speed").fill("50");
    await page.getByRole("button",{name:"Apply to strip"}).click();
    await page.waitForFunction(() => window.calls.length === 1);
    const call = await page.evaluate(() => window.calls[0]);
    assert.equal(call.service,"apply_diy");
    assert.equal(call.data.animation,"breathe");
    assert.equal(call.data.speed,50);
    assert.deepEqual(call.data.groups,[{rgb:[255,0,0],segments:[0]},{rgb:[0,0,255],segments:[1]}]);
    await page.getByRole("button",{name:"Eraser",exact:true}).click();
    await page.locator(".segment").nth(0).tap();
    await page.getByRole("button",{name:"Undo",exact:true}).click();
    assert.equal(await page.evaluate(() => document.querySelector("govee-h617a-card").segments[0]),"#ff0000");
    await page.evaluate(() => window.failNext = true);
    await page.getByRole("button",{name:"Apply to strip"}).click();
    await page.waitForFunction(() => document.querySelector("govee-h617a-card").shadowRoot.querySelector("#message").textContent.includes("Simulated BLE"));
    // HA refreshes must not overwrite an open draft.
    await page.evaluate(() => { const c=document.querySelector("govee-h617a-card"); c.hass={...c._hass}; });
    assert.equal(await page.evaluate(() => document.querySelector("govee-h617a-card").segments[0]),"#ff0000");
    const overflow = await page.locator("dialog").evaluate(el=>el.scrollWidth > el.clientWidth);
    assert.equal(overflow,false);
    await page.screenshot({path:"/private/tmp/govee-diy-mobile.png"});
    await page.getByRole("button",{name:"Clear",exact:true}).click();
    assert.equal(await page.locator("#apply").isDisabled(),true);
    await page.evaluate(() => {
      const c=document.querySelector("govee-h617a-card");
      c.segments=Array.from({length:15},(_,i)=>"#"+(i+10).toString(16).padStart(6,"0"));
      c.draw();
    });
    assert.equal(await page.locator("#apply").isDisabled(),false);
    await page.getByRole("button",{name:"Apply to strip"}).click();
    const large = await page.evaluate(() => window.calls.at(-1));
    assert.equal(large.data.groups.length,15);
    assert.deepEqual(large.data.groups.map(g => g.segments), Array.from({length:15},(_,i)=>[i]));
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("dialog").isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log("Card checks passed: touch paint, no premature writes, Apply payload, erase/undo, error feedback, draft retention, 15 colours, empty guard, mobile layout, Escape.");
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
