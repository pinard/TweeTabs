# -*- coding: utf-8 -*-

ing = Id_input(configdir + '/20')
ers = Id_input(configdir + '/03')
ing = Following()
ers = Followers()

ing.set_name('…ing')
ers.set_name('…ers')

union = Union(ing, ers)
inter = Intersection(ing, ers)
diff = Difference(ing, ers)

union.set_name('∨')
inter.set_name('∧')
diff.set_name('∧¬')
