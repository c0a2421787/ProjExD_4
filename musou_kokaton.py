import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        # 無敵状態の管理
        self.state = "normal"  # "normal" or "hyper"
        self.hyper_life = 0  # 無敵状態の残り時間

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        
        # 無敵状態の処理
        if self.state == "hyper":
            # 無敵画像を表示（ラプラシアン フィルタで変形）
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life <= 0:
                self.state = "normal"
                self.image = self.imgs[self.dire]
        
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect) 
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: float = 0):
        """
        ビーム画像Surfaceを生成する
        引数1 bird：ビームを放つこうかとん
        引数2 angle0：回転角度（デフォルト0）
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        # [cite_start]angle0を加算して、放射状の角度を計算 [cite: 535]
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    弾幕（複数方向へのビーム）に関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        引数1 bird：こうかとんオブジェクト
        引数2 num：ビームの発射数
        """
        self.bird = bird
        self.num = num

    def gen_beams(self) -> list[Beam]:
        """
        指定された角度範囲と数に基づいてBeamオブジェクトのリストを生成する
        戻り値：Beamオブジェクトのリスト
        """
        check_lst = list()
        # [cite_start]-50度から+50度の範囲（100度幅）を(num-1)分割するステップを計算 [cite: 541-547]
        step = int(100 / (self.num - 1))
        # [cite_start]-50度から+51度までstep刻みでループ [cite: 538]
        for angle in range(-50, 51, step):
            check_lst.append(Beam(self.bird, angle))
        return check_lst


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life: int):
        """
        重力場Surfaceを生成する
        引数 life：発動時間
        """
        super().__init__()
        self.life = life
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(200)
        self.rect = self.image.get_rect()

    def update(self):
        """
        発動時間を1減算し，0未満になったらkillする
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 1000000
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Wall(pg.sprite.Sprite): # 追加機能５
    """
    防御壁に関するクラス
    こうかとんの前に防御壁を出現させ，着弾を防ぐ
    """
    def __init__(self, bird: Bird, life: int): # 追加機能５
        """
        防御壁Surfaceを生成する
        引数1 bird：防御壁を出現させるこうかとん
        引数2 life：防御壁の持続時間（フレーム数）
        """
        super().__init__() # 追加機能５
        self.life = life  # 防御壁の持続時間を設定 追加機能５
        w = 20  # 防御壁の幅
        h = bird.rect.height*2 # 防御壁の高さ
        self.image = pg.Surface((w, h), pg.SRCALPHA) # 防御壁Surfaceを生成
        self.image.fill((0, 255, 255)) # 防御壁の色を設定
        pg.draw.rect(self.image, (0, 255, 255), self.image.get_rect()) # 防御壁を描画
        vx , vy = bird.dire  # こうかとんの向きベクトルを取得
        angle = math.degrees(math.atan2(-vy, vx)) # こうかとんの向きベクトルから角度を計算
        self.image = pg.transform.rotozoom(self.image, angle, 1.0) # 防御壁を回転
        self.rect = self.image.get_rect() # 防御壁のRectを取得

        between = bird.rect.width # こうかとんと防御壁の間隔を設定
        self.rect.centerx = bird.rect.centerx + between * vx # 防御壁のx座標を設定
        self.rect.centery = bird.rect.centery + between * vy # 防御壁のy座標を設定

    def update(self): #追加機能５
        self.life -= 1 # 防御壁の持続時間を1減算
        if self.life <= 0: # 持続時間が0以下になったら
            self.kill() # 防御壁を消す

        

class EMP:  # 追加機能3
    """
    スコアが20以上の状態で電磁パルスを発動するクラス
    敵機と爆弾を無効化
    画面に黄色い矩形を0.05秒表示
    消費スコア:20
    """
    def __init__(self, emys:pg.sprite.Group, bombs: pg.sprite.Group, screen:pg.Surface, score: "Score"):
        self.emys = emys
        self.bombs = bombs
        self.screen = screen
        self.score = score
        self.active = False  # 描画中かどうか
        self.timer = 0  # 表示時間カウント
    
    def activate(self):
        """
        EMP 発動関数
        """
        if self.score.value < 20:  # スコア不足(スコアが20以下)はなにもしない
            return
        
        self.score.value -= 20  # スコアを20消費する

        for emy in self.emys:  # 敵機を無効化
            emy.interval = float("inf")  # 爆弾を投下しなくなる
            emy.image = pg.transform.laplacian(emy.image)  # ラプラシアンフィルタをかける

        for bomb in self.bombs:  # 爆弾を無効化
            bomb.speed *= 0.5  # 爆弾の速さを半減する
            bomb.state = "inactive"  # 衝突時に爆発しない処理

        self.active = True  # 描画中です
        self.timer = 3  # 約0.05秒のタイマ

    def update(self):
        """
        半透明の黄色い矩形の表示（毎フレーム呼ぶ）
        """
        if not self.active:
            return
        rect = pg.Surface((WIDTH,HEIGHT), pg.SRCALPHA)  # 黄色半透明の矩形
        rect.fill((255,255,0,100))
        self.screen.blit(rect,(0,0))
        self.timer -= 1
        if self.timer <= 0:
            self.active = False  # 描画終わり  



def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    walls = pg.sprite.Group()  # 防御壁グループを作成 追加機能５
    gravities = pg.sprite.Group()
    emp = EMP(emys,bombs,screen,score)  

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                # スペースキーでビーム（通常・弾幕）
                if event.key == pg.K_SPACE:
                    # [cite_start]左Shiftキーが押されているか判定 [cite: 527]
                    if key_lst[pg.K_LSHIFT]:
                        # [cite_start]弾幕発動：NeoBeamを生成し、ビームリストを取得してグループに追加 [cite: 539]
                        nb = NeoBeam(bird, 5)  # ビーム数5
                        beams.add(nb.gen_beams())
                    else:
                        # 通常発射
                        beams.add(Beam(bird))
                
                # リターンキーで重力場
                if event.key == pg.K_RETURN and score.value > 200:
                    gravities.add(Gravity(400))
                    score.value -= 200
                
                # 右Shiftキーで無敵状態
                if event.key == pg.K_RSHIFT and score.value > 100 and bird.state == "normal":
                    bird.state = "hyper"
                    bird.hyper_life = 500
                    score.value -= 100

                # eキーでEMP
                if event.key == pg.K_e:  # 追加機能3,eキー押下時の処理
                    emp.activate()

        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            if getattr(bomb, "state","active") == "inactive":
                continue  # 爆発せずに消える
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
            

        # 重力場と爆弾・敵機の衝突判定
        for bomb in pg.sprite.groupcollide(bombs, gravities, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1
        for emy in pg.sprite.groupcollide(emys, gravities, True, False).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10

        # こうかとんと衝突した爆弾の処理（無敵判定込み）
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper":
                # 無敵状態：爆弾を爆発させてスコア加算
                exps.add(Explosion(bomb, 50))
                score.value += 1
            else:
                # 通常状態：ゲームオーバー
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        if key_lst[pg.K_s] and score.value > 50 and len(walls) == 0:  #スコアが50点以上で防御壁が存在しない場合sキーで起動 追加機能５
            walls.add(Wall(bird, 400))  # 防御壁を出現させる 追加機能５
            score.value -= 50  # スコアを50点減算 追加機能５

        for wall in walls:  # 防御壁ごとに処理 追加機能５
            hit_bombs = pg.sprite.spritecollide(wall, bombs, True) # 防御壁と衝突した爆弾リスト 追加機能５
            for bomb in hit_bombs: # 防御壁と衝突した爆弾ごとに処理 追加機能５
                exps.add(Explosion(bomb, 50)) # 爆発エフェクト 追加機能５
    
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        
        # Gravityの描画をExplosionやScoreより前に
        gravities.update()
        gravities.draw(screen)

        exps.update()
        exps.draw(screen)
        
        score.update(screen)

        walls.update() # 防御壁を更新 追加機能５
        walls.draw(screen) # 防御壁を描画 追加機能５

        
        emp.update()
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()