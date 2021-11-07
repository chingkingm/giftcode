import asyncio
from logging import exception, info, log
import os, yaml, time
from posixpath import join
from re import split
from loguru import logger
import hoshino
from hoshino import Service, priv

sv = Service('兑换码', manage_priv=priv.ADMIN, enable_on_default=True)


def get_code():
    with open(f'{os.path.dirname(__file__)}/giftcode.yml', encoding='utf8') as f:
        codelist = yaml.load(f, Loader=yaml.FullLoader)
        f.close()
        return codelist


def save_code(codelist):
    with open(f'{os.path.dirname(__file__)}/giftcode.yml', 'w', encoding='utf8') as f:
        yaml.dump(codelist, f, allow_unicode=True)


def add_code(game, code, time, awards):
    """添加兑换码，game:游戏；code:码；time:失效时间；awards:奖励"""
    del_code()
    codelist = get_code()
    try:
        codelist[game][code] = [time, awards]
    except KeyError:
        codelist[game] = {}
        codelist[game][code] = [time, awards]
    finally:
        save_code(codelist)


def fommat_code(game):
    """格式化输出"""
    del_code()
    ret = ''
    codelist = get_code()
    if codelist[game]:
        ret = f'{game}\n'
        for code in codelist[game]:
            end_time = time.strftime('%Y/%m/%d,%H:%M:%S', time.localtime(codelist[game][code][0]))
            awards = codelist[game][code][1]
            ret = f'{ret}{code}\t奖励:{awards}\t有效期至{end_time}\n'
    return ret


def del_code():
    """删除过期兑换码"""
    now = time.time()
    codelist = get_code()
    for game in list(codelist):  # dict在遍历时不能更改元素
        for code in list(codelist[game]):
            end_time = codelist[game][code][0]
            if end_time < now:
                logger.info(f'兑换码{code}已过期。')
                codelist[game].pop(code)
    save_code(codelist)


# add_code('原神','hufhuwhajsn',time.time(),'ttj*5')
# add_code('崩坏3','zohhbfuqgeeu',time.time(),'shui*333')    
@sv.on_prefix('查看兑换码')
async def show_giftcode(bot, ev):
    rec_game = ev.message.extract_plain_text()
    codelist = get_code()
    msg = ''
    if not rec_game:
        rec_game = '任何游戏'
        for g in codelist:
            msg = f'{msg}{fommat_code(game=g)}'
    elif rec_game in codelist:
        msg = f'{msg}{fommat_code(rec_game)}'
    else:
        msg = f'不存在游戏{rec_game}的兑换码'
    if not msg:
        await bot.send(ev, f'现在没有{rec_game}的兑换码，请联系维护组添加。')
    else:
        await bot.send(ev, msg)


@sv.on_prefix('添加兑换码')
async def add_giftcode(bot, ev):
    if priv.get_user_priv(ev) < priv.ADMIN:
        await bot.send(ev, '为避免滥用，添加功能仅限管理员使用。')
        return
    message = ev.message.extract_plain_text()
    logger.info(message)
    # mes = message.split()
    # mes = ''.join(mes).split(',')
    # mes = ''.join(mes).split('，')
    if ',' in message:
        mes = message.split(',')
    elif '，' in message:
        mes = message.split('，')
    else:
        mes = message.split()
    logger.info(mes)
    if len(mes) != 4:
        await bot.send(ev,
                       f'格式不正确，仅支持中英文逗号或空格作为分隔符。例如“添加兑换码崩坏3 ZANLDMK7KCGF 2021/11/12/23/59 金币*20000、高级进化材料箱*2、双子灵魂结晶*3”')
        return
    else:
        # 格式化时间
        rec_time = mes[2]
        if '/' in rec_time:
            try:
                mtime = time.mktime(time.strptime(rec_time, '%Y/%m/%d/%H/%M'))
                if mtime < time.time():
                    await bot.send(ev, f'{mes[2]}已经过去了，请检查输入的时间')
                    return
                else:
                    mes[2] = mtime
            except ValueError:
                await bot.send(ev, f'时间格式不正确，请使用/作为分割，例如“2021/11/04/12/00”.')
                return
        else:
            await bot.send(ev, f'时间格式不正确，请使用/作为分割，例如“2021/11/04/12/00”.')
            return
    add_code(mes[0], mes[1], mes[2], mes[3])
    sv_groups = await sv.get_enable_groups()
    logger.info(sv_groups)
    for sid in hoshino.get_self_ids():
        for group_num in sv_groups.keys():
            await asyncio.sleep(0.5)
            msg = f'兑换码已更新\n{message}'
            await bot.send_group_msg(group_id=group_num, message=msg, self_id=sid)
    await bot.send(ev, f'{mes[0]}兑换码{mes[1]}添加成功。', at_sender=True)


@sv.scheduled_job('cron', hour='11,23', minute='10')
# @sv.on_fullmatch('检查2')
async def check_code():
    del_code()
    codelist = get_code()
    now = time.time()
    bot = hoshino.get_bot()
    sv_groups = await sv.get_enable_groups()
    msg = ''
    for game in codelist:
        for code in codelist[game]:
            end_time = codelist[game][code][0]
            if (end_time - now) < 3600:
                logger.info(f'{game}:{code}即将过期')
                end_time = time.strftime('%Y/%m/%d,%H:%M:%S', time.localtime(codelist[game][code][0]))
                msg = msg + (f'{game}|{code}|{end_time}\n')
                logger.info(f'in for msg{msg}')
    if msg:
        logger.info(f'in if msg{msg}')
        msg = f'{msg}\n以上兑换码即将到期，请注意使用。'
        logger.info(f'send msg{msg}')
        for sid in hoshino.get_self_ids():
            for group_num in sv_groups.keys():
                await asyncio.sleep(0.5)
                await bot.send_group_msg(group_id=group_num, message=msg, self_id=sid)
