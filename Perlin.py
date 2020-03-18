import noise
import decimal


def drange(x, y, jump):
    while x < y:
        yield float(x)
        x += decimal.Decimal(jump)


if __name__ == '__main__':
    # Print 2d simplex noise in from x, y in 0..1 with step 0.1
    for x in drange(0, 1.01, 0.1):
        for y in drange(0, 1.01, 0.1):
            print(f"[{x:.2},{y:.2}] {noise.snoise2(x, y)}")
