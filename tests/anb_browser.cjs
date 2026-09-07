// Run with Node and NODE_PATH pointing to the installed Playwright package.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[]; page.on('pageerror', error=>errors.push(error.message));
  await page.goto('http://localhost:8777');
  await page.locator('article').filter({hasText:'ANB Style'}).getByRole('button').click();
  await page.waitForSelector('#preview');
  await page.evaluate(()=>document.fonts.ready);

  assert.equal(await page.locator('#openProject').count(),0);
  assert.equal(await page.locator('#saveProject').count(),0);
  assert.equal(await page.locator('#downloadOne').count(),0);
  assert.equal(await page.locator('#sendTelegram').count(),1);
  assert.equal(await page.locator('#bold').count(),0);
  assert.equal(await page.locator('#accent').count(),0);

  await page.locator('#directTitle').fill('IDEIAS QUE MERECEM ATENÇÃO.');
  for(const layout of ['cover','editorial','band','side','manifesto','text']){
    await page.locator('#layout').selectOption(layout);
    assert.equal(await page.locator('#status').getAttribute('class'),'status');
  }

  await page.locator('#directBody').fill('Texto longo. '.repeat(1000));
  assert.match(await page.locator('#status').innerText(),/ultrapassou/);
  await page.locator('#downloadAll').click();
  assert.match(await page.locator('#toast').innerText(),/Revise/);

  await page.locator('#directBody').fill('Uma ideia clara para editar diretamente.');
  await page.locator('#directBody').focus();
  await page.locator('#fontSize').fill('55');
  await page.locator('#lineHeight').fill('61');
  await page.locator('#letterSpacing').fill('-0.035');
  assert.deepEqual(await page.evaluate(()=>slides[current].textStyles.body),{fontSize:55,lineHeight:61,letterSpacing:-0.035});
  await page.locator('#directBody').evaluate(el=>{const text=el.firstChild,range=document.createRange();range.setStart(text,0);range.setEnd(text,3);const selection=getSelection();selection.removeAllRanges();selection.addRange(range)});
  await page.keyboard.press('Control+b');
  assert.match(await page.locator('#directBody').innerHTML(),/<b>|<strong>/);

  await page.locator('#layout').selectOption('editorial');
  fs.mkdirSync('.tmp/anb-qa',{recursive:true});
  const png=Buffer.from(await page.evaluate(()=>{const target=document.createElement('canvas');render(slides[current],target);return target.toDataURL().split(',')[1]}),'base64');
  fs.writeFileSync('.tmp/anb-qa/slide.png',png);
  assert.equal(png.readUInt32BE(16),1080); assert.equal(png.readUInt32BE(20),1350);
  await page.locator('#photo').setInputFiles('.tmp/anb-qa/slide.png');
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('Foto adicionada'));
  await page.locator('#focusY').fill('80');
  await page.locator('#zoom').fill('130');
  const clean=await page.locator('#preview').evaluate(canvas=>canvas.toDataURL());
  await page.locator('#vortex').check();
  assert.equal(await page.locator('#status').getAttribute('class'),'status');
  assert.notEqual(await page.locator('#preview').evaluate(canvas=>canvas.toDataURL()),clean);
  await page.locator('#vortexStrength').fill('65');
  await page.locator('#vortexX').fill('40');
  await page.locator('#vortexRadius').fill('35');
  await page.locator('.slide-button').nth(1).click();
  assert.equal(await page.locator('#vortex').isChecked(),false);
  await page.locator('.slide-button').nth(0).click();
  assert.equal(await page.locator('#vortex').isChecked(),true);

  await page.locator('#directBody').fill('Conteúdo persistente após reload');
  await page.locator('#directBody').focus();
  await page.locator('#fontSize').fill('53');
  await page.waitForTimeout(350);
  await page.reload();
  await page.waitForSelector('#directBody');
  assert.match(await page.locator('#directBody').innerText(),/Conteúdo persistente após reload/);
  await page.locator('#directBody').focus();
  assert.equal(await page.locator('#fontSize').inputValue(),'53');

  let telegramPayload;
  await page.route('**/api/telegram/send',async route=>{telegramPayload=route.request().postDataJSON();await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true})})});
  await page.locator('#sendTelegram').click();
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('enviados ao Telegram'));
  assert.equal(telegramPayload.images_b64.length,10);

  page.once('dialog',dialog=>dialog.accept());
  await page.locator('#resetCarousel').click();
  await page.reload();
  assert.doesNotMatch(await page.locator('#directBody').innerText(),/Conteúdo persistente/);

  const zipPromise=page.waitForEvent('download');
  await page.locator('#downloadAll').click();
  await (await zipPromise).saveAs('.tmp/anb-qa/slides.zip');
  await page.screenshot({path:'.tmp/anb-qa/editor.png'});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#format').selectOption('1440');
  assert.equal(await page.locator('#preview').getAttribute('height'),'1440');
  assert.deepEqual(errors,[]);
  console.log('ANB browser: direct editing, Ctrl+B, typography controls, autosave/reset, Telegram, Vortex, ZIP, both ratios, responsive layout and no JS errors PASS');
  await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
